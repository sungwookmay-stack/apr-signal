# Collector recovery

Monthly KITA UI checks compare the displayed route-specific month and price to the loaded data. Offline fixtures cover month rollover, changed prices, independent east/west delays and absent data. Saved-data checks also run before provider calls.

The workflow stores demand and Top50 recovery artifacts immediately after the corresponding collectors, including when those steps fail. They contain only data/demand.json, data/top50.json and state/decodo_top50.json; no credentials, logs or checkout directories. Retention is 14 days. A later unrelated smoke failure no longer removes the only surviving copy of successfully collected data. Abrupt runner termination or artifact service failure can still prevent backup.

Artifacts are recovery candidates, not automatically published data. Check run ID, observed dates, country/category, rank completeness, source identity, history and local attempt ledger before restoring. A failed or excluded-day collector can produce unchanged/partial files. Preserve previous complete observations and attempt reservations. Do not reset the budget ledger or rerun paid collectors merely to recover a failed publication. Never use this recovery path to overwrite private KRX snapshots. Public Pages publishing remains stopped.
