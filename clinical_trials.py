"""Free public ClinicalTrials.gov registry observations, not regulatory filings."""
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://clinicaltrials.gov/api/v2/studies"
SPONSORS = {"aprcoltd"}

def normalized(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())

def extract(study):
    p = study["protocolSection"]
    sponsor = p["sponsorCollaboratorsModule"]["leadSponsor"]
    if normalized(sponsor["name"]) not in SPONSORS or sponsor.get("class") != "INDUSTRY":
        return None
    i, s = p["identificationModule"], p["statusModule"]
    nct = i["nctId"]
    if not re.fullmatch(r"NCT[0-9]{8}", nct):
        raise ValueError("invalid_nct")
    return dict(nct_id=nct, sponsor=sponsor["name"], title=i["briefTitle"],
                protocol_id=i.get("orgStudyIdInfo", {}).get("id"),
                status=s["overallStatus"], first_posted=s.get("studyFirstPostDateStruct", {}).get("date"),
                updated=s.get("lastUpdatePostDateStruct", {}).get("date"),
                start=s.get("startDateStruct", {}), completion=s.get("completionDateStruct", {}),
                enrollment=p.get("designModule", {}).get("enrollmentInfo", {}),
                summary=p.get("descriptionModule", {}).get("briefSummary", ""),
                url="https://clinicaltrials.gov/study/" + nct)

def collect(fetch=None):
    if fetch is None:
        def fetch(url):
            with urllib.request.urlopen(url, timeout=45) as r:
                return json.load(r)
    records, tokens = {}, set()
    params = {"query.spons": "APR Co., Ltd.", "pageSize": 100, "format": "json"}
    for _ in range(20):
        data = fetch(API + "?" + urllib.parse.urlencode(params))
        if not isinstance(data.get("studies"), list):
            raise ValueError("invalid_response")
        for study in data["studies"]:
            row = extract(study)
            if row:
                records[row["nct_id"]] = row
        token = data.get("nextPageToken")
        if not token:
            return list(records.values())
        if token in tokens:
            raise ValueError("pagination_loop")
        tokens.add(token)
        params["pageToken"] = token
    raise ValueError("pagination_limit")

def snapshot(previous, records, now):
    old = {r["nct_id"]: r for r in previous.get("records", [])}
    events = previous.get("events", [])[:]
    for r in records:
        before = old.get(r["nct_id"])
        r["first_seen"] = (before or {}).get("first_seen", now)
        r["last_seen"] = now
        r["present"] = True
        changes = [k for k in ("status", "updated", "completion", "enrollment", "title") if before and before.get(k) != r.get(k)]
        if not before or changes:
            events.append(dict(nct_id=r["nct_id"], at=now, kind="updated" if before else "first_observed", fields=changes))
    current_ids = {r["nct_id"] for r in records}
    for key, old_row in old.items():
        if key not in current_ids:
            records.append(dict(old_row, present=False))
    return dict(schema_version=1, status="ok", checked_at=now, last_success_at=now,
                observed_count=len(current_ids), records=records, events=events[-100:])

def main():
    path = Path("data/clinical_trials.json")
    previous = json.loads(path.read_text()) if path.exists() else {}
    now = datetime.now(timezone.utc).isoformat()
    try:
        result = snapshot(previous, collect(), now)
    except Exception as exc:
        result = dict(previous, schema_version=1, status="error", checked_at=now,
                      observed_count=None, error_type=type(exc).__name__)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("ClinicalTrials.gov:", result["status"], "observed", result["observed_count"])

if __name__ == "__main__":
    main()
