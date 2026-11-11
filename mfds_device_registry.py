"""MFDS device registry adapter; absence is not denial, discovery is not approval.

Schema checked against data.go.kr dataset 15057456 on 2026-11-11.
This module is deliberately not wired into the public site until the service key
is approved and the first real response/schema and company identities verified.
No secret or full request URL is serialized in public output.
"""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import json
import os
import re
from pathlib import Path
from urllib import error, parse, request

SOURCE_URL = "https://www.data.go.kr/data/15057456/openapi.do"
API_URL = ("https://apis.data.go.kr/1471000/MdlpPrdlstPrmisnInfoService06/"
           "getMdlpPrdlstPrmisnItem05")
SOURCE = "MFDS medical-device product registry API 15057456"
DEFAULT_COMPANIES = ("에이피알", "에이피알팩토리")
APR_BRNO = "2208889441"  # Public company identifier, APR official website footer.
FIELDS = {
    "registry_id": "MDEQ_PRDLST_SN", "permit_number": "PRDUCT_PRMISN_NO",
    "company": "ENTRPS", "business_number": "BRNO", "product": "PRDUCT",
    "model": "TYPE_NAME", "grade": "GRADE", "classification": "MEA_CLASS_NO",
    "permitted_use": "USE_PURPS", "permit_date": "PRMISN_DT",
    "registry_changed_at": "CHG_DT", "cancellation_code_raw": "RTRCN_DSCTN_DIVS_CD",
    "cancellation_at_raw": "RTRCN_DSCTN_DT", "manufacturer": "MANUF_NM",
    "commissioning_company": "MNFT_CLNT_NM",
}

class RegistryError(Exception):
    """Safe code only: never hold a secret-bearing HTTP URL or response body."""


def company_key(value):
    value = re.sub(r"\s+", "", str(value or ""))
    return value.replace("주식회사", "").replace("(주)", "").replace("㈜", "")


def _text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def normalize(row):
    if not isinstance(row, dict):
        raise RegistryError("invalid_record")
    out = {name: _text(row.get(field)) for name, field in FIELDS.items()}
    if not out["registry_id"] and not out["permit_number"]:
        raise RegistryError("missing_record_identity")
    out["record_key"] = ("id:" + out["registry_id"] if out["registry_id"] else
                         "permit:" + out["permit_number"])
    name = company_key(out["company"])
    brno = re.sub(r"\D", "", out["business_number"] or "")
    if brno == APR_BRNO:
        out["company_match"] = "public_business_number"
    elif name in DEFAULT_COMPANIES:
        out["company_match"] = "exact_company_name_requires_initial_identity_review"
    else:
        out["company_match"] = "candidate_requires_review"
    # The verified API schema has no explicit export-only/domestic scope field.
    # A permit date, grade or Korean permit number cannot settle this question.
    out["domestic_market_authorization"] = "not_verified"
    out["export_scope"] = "not_verified"
    out["source"] = SOURCE
    out["source_url"] = SOURCE_URL
    return out


def parse_page(payload):
    if not isinstance(payload, dict):
        raise RegistryError("invalid_response")
    wrapper = payload.get("response", payload)
    if not isinstance(wrapper, dict):
        raise RegistryError("invalid_response")
    header = wrapper.get("header")
    body = wrapper.get("body")
    if not isinstance(header, dict) or not isinstance(body, dict):
        raise RegistryError("invalid_response")
    code = str(header.get("resultCode", ""))
    if code not in {"00", "0", "0000"}:
        if code in {"20", "21", "30", "31", "32", "33"}:
            raise RegistryError("authorization_denied")
        raise RegistryError("api_business_error")
    try:
        total = int(body["totalCount"])
    except (KeyError, TypeError, ValueError):
        raise RegistryError("invalid_total_count") from None
    if total < 0:
        raise RegistryError("invalid_total_count")
    items = body.get("items")
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    if items in (None, ""):
        items = []
    if not isinstance(items, list):
        raise RegistryError("invalid_items")
    return [normalize(x) for x in items], total


def _http(url):
    with request.urlopen(url, timeout=25) as response:
        return response.read()


def fetch_company(company, key, *, http=_http, max_pages=10):
    rows, seen, expected = [], set(), None
    for page in range(1, max_pages + 1):
        query = parse.urlencode({"serviceKey": parse.unquote(key), "type": "json",
                                 "pageNo": page, "numOfRows": 100, "ENTRPS": company})
        try:
            payload = json.loads(http(API_URL + "?" + query))
        except error.HTTPError as exc:
            raise RegistryError("authorization_denied" if exc.code in (401, 403)
                                else "http_error") from None
        except (error.URLError, TimeoutError, OSError):
            raise RegistryError("network_error") from None
        except (ValueError, TypeError):
            raise RegistryError("invalid_json") from None
        batch, total = parse_page(payload)
        if expected is None:
            expected = total
        elif total != expected:
            raise RegistryError("pagination_changed")
        keys = [r["record_key"] for r in batch]
        if len(set(keys)) != len(keys) or any(k in seen for k in keys):
            raise RegistryError("duplicate_page_records")
        seen.update(keys)
        rows.extend(batch)
        if len(rows) == total:
            return rows
        if len(rows) > total or not batch:
            raise RegistryError("incomplete_pagination")
    raise RegistryError("page_limit_reached")


def update_snapshot(previous=None, *, key=None, http=_http, checked_at=None):
    """Run a full company-name scan; keep the last full snapshot on any failure.

    Full history is retained when a record disappears. Such disappearance is
    never interpreted as withdrawal. First scan creates baseline, not alerts.
    """
    previous = previous or {}
    now = checked_at or dt.datetime.now(dt.timezone.utc).isoformat()
    out = copy.deepcopy(previous)
    out.update({"schema_version": 1, "source": SOURCE, "source_url": SOURCE_URL,
                "checked_at": now, "events": [], "current_scan_complete": False,
                "observed_count": None, "candidate_count": None,
                "queries": list(DEFAULT_COMPANIES),
                "limitations": [
                    "신규 발견은 신규 허가가 아님. 허가일·변경일·최초 관측일을 구분합니다.",
                    "수출전용/국내 판매 범위는 API만으로 검증되지 않습니다.",
                    "미검색·조회 실패는 무허가나 신청 반려를 의미하지 않습니다.",
                    "심사 중 신청과 예정 승인일은 이 공개 등록부로 확인할 수 없습니다.",
                    "품목허가·인증·신고, 공장 GMP, 임상시험 승인 및 출시·매출은 별개입니다.",
                    "업체명 일치 후보는 처음에 사업자번호·공시로 실체를 대조해야 합니다."]})
    out.setdefault("records", [])
    out.setdefault("last_success_at", None)
    out.setdefault("event_history", [])
    key = key if key is not None else os.getenv("MFDS_DEVICE_API_KEY", "")
    if not key:
        out["status"] = "not_configured"
        return out
    fresh = {}
    try:
        for company in DEFAULT_COMPANIES:
            for row in fetch_company(company, key, http=http):
                old = fresh.get(row["record_key"])
                if old is not None and old != row:
                    raise RegistryError("conflicting_records")
                fresh[row["record_key"]] = row
    except RegistryError as exc:
        out["status"] = str(exc)
        return out
    baseline = not previous.get("last_success_at")
    prior = {r["record_key"]: r for r in previous.get("records", [])}
    records = []
    for identity, row in sorted(fresh.items()):
        old = prior.get(identity)
        changed = [] if old is None else [k for k in FIELDS if old.get(k) != row.get(k)]
        row.update({"first_seen_at": old.get("first_seen_at", now) if old else now,
                    "last_seen_at": now, "presence": "observed"})
        records.append(row)
        if not baseline and old is None:
            out["events"].append({"kind": "newly_observed_registry_record",
                                  "record_key": identity, "at": now})
        elif not baseline and changed:
            out["events"].append({"kind": "registry_record_changed",
                                  "record_key": identity, "fields": changed, "at": now})
    for identity, old in sorted(prior.items()):
        if identity not in fresh:
            old = copy.deepcopy(old)
            if old.get("presence") != "not_observed_in_latest_full_scan":
                out["events"].append({"kind": "not_observed_requires_review",
                                      "record_key": identity, "at": now})
            old["presence"] = "not_observed_in_latest_full_scan"
            records.append(old)
    out["event_history"] = (out["event_history"] + out["events"])[-5000:]
    out.update({"status": "ok", "current_scan_complete": True,
                "last_success_at": now, "records": records,
                "is_initial_baseline": baseline, "observed_count": len(fresh),
                "candidate_count": sum(r["company_match"] == "candidate_requires_review"
                                       for r in fresh.values())})
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/mfds_devices.json")
    args = parser.parse_args()
    path = Path(args.output)
    previous = json.loads(path.read_text()) if path.exists() else {}
    snapshot = update_snapshot(previous)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)
    print(json.dumps({"status": snapshot["status"],
                      "last_success_at": snapshot["last_success_at"]}))


if __name__ == "__main__":
    main()
