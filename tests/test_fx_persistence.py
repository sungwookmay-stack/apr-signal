import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import update_data as updater


DATES = ("2026-11-13", "2026-11-18", "2026-11-19")
ZIP = "ECB official historical CSV ZIP"
CSV = "ECB official historical CSV"


def fx_tables(i, usd=1330, eur=1460):
    return {"USD": {DATES[i]: usd}, "EUR": {DATES[i]: eur}}


def sources(label):
    return {"USD": label+" (EUR/KRW ÷ EUR/USD)" if label.startswith("ECB") else label,
            "EUR": label}


def snapshot(i, close=243000):
    return {"fx": updater.fx_rows(fx_tables(i)),
            "meta": {"stock_source": "test", "fx_sources": sources(ZIP)},
            "series": [{"date": DATES[-1], "close_krw": close, "volume": 9}],
            "logistics": {"sea": [], "air": []}}


class TestFxPersistence(unittest.TestCase):
    def test_older_provider_cannot_roll_back_each_currency(self):
        fx, labels, retained = updater.reconcile_fx(
            fx_tables(1), sources(ZIP), fx_tables(0), sources(CSV))
        self.assertEqual(max(fx["USD"]), DATES[1])
        self.assertEqual(max(fx["EUR"]), DATES[1])
        self.assertEqual(retained, ["USD", "EUR"])
        self.assertEqual(labels, sources(ZIP))

    def test_overlap_official_value_preserved_and_extends(self):
        old, new = fx_tables(1), fx_tables(2, 1328, 1461)
        new["USD"][DATES[1]] = 1331
        fx, labels, retained = updater.reconcile_fx(old, sources(ZIP), new, sources(CSV))
        self.assertEqual(fx["USD"], {DATES[1]: 1330, DATES[2]: 1328})
        self.assertEqual(fx["EUR"][DATES[2]], 1461)
        self.assertEqual(labels, sources(ZIP))
        self.assertEqual(retained, [])

    def test_fallback_does_not_replace_official_even_if_newer(self):
        fx, labels, _ = updater.reconcile_fx(fx_tables(1), sources(ZIP),
                                             fx_tables(2), sources("Proxy"))
        self.assertEqual(fx, fx_tables(1))
        self.assertEqual(labels, sources(ZIP))

    def test_price_refresh_reuses_newest_saved_fx_without_fx_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, row in [("data.json", snapshot(0)),
                              ("market.json", snapshot(1, close=1))]:
                (root / name).write_text(json.dumps(row))
            with patch.object(updater, "fetch_stock", return_value=([],None,[])), \
                 patch.object(updater, "fetch_fx", side_effect=AssertionError("No call")), \
                 patch.object(updater, "save"):
                data = updater.update(root, refresh_fx=False, refresh_freight=False)
            self.assertEqual(data["meta"]["usd_fx_last"], DATES[1])
            self.assertEqual(data["series"][-1]["close_krw"], 243000)
            self.assertEqual(data["series"][-1]["fx_usd_date"], DATES[1])
