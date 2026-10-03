"""Create and run the CTAS SQL pipeline against poc_wh."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from demo_proof import (
    WORKSPACE_ID,
    BASE,
    ROOT,
    create_pipeline,
    get_token,
    headers,
    run_pipeline,
)

SQL_JSON = ROOT / "demo_json" / "05_ctas_sql.json"


def query_activity_runs(session: requests.Session, token: str, pipeline_run_id: str) -> dict:
    url = (
        f"{BASE}/workspaces/{WORKSPACE_ID}/datapipelines/pipelineruns/"
        f"{pipeline_run_id}/queryactivityruns"
    )
    resp = session.post(url, headers=headers(token), json={})
    try:
        return {"httpStatus": resp.status_code, "body": resp.json()}
    except ValueError:
        return {"httpStatus": resp.status_code, "body": resp.text}


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"Demo_CTAS_SQL_{stamp}"
    token = get_token()
    session = requests.Session()

    print(f"CREATE {name}")
    created = create_pipeline(session, token, name, SQL_JSON)
    print(f"  HTTP {created['httpStatus']}  id={created.get('id')}")
    if created.get("createFailed"):
        print("  Response:", created["response"])
        Path("demo_ctas_results.json").write_text(json.dumps(created, indent=2), encoding="utf-8")
        return

    print("RUN")
    job = run_pipeline(session, token, created["id"], timeout_s=600)
    print(f"  Start HTTP {job['httpStatus']}  jobStatus={job.get('jobStatus')}")
    if job.get("job"):
        print("  failureReason:", job["job"].get("failureReason"))

    run_id = (job.get("job") or {}).get("id")
    activities = None
    if run_id:
        activities = query_activity_runs(session, token, run_id)
        body = activities.get("body") or {}
        values = body.get("value") if isinstance(body, dict) else None
        if values:
            for act in values:
                print(
                    f"  activity {act.get('activityName')}: "
                    f"{act.get('status')}  {act.get('error') or ''}"
                )

    out = {
        "pipeline": created,
        "run": job,
        "activities": activities,
    }
    path = ROOT / "demo_ctas_results.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
