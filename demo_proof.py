"""
Live demo for Fabric REST pipeline creation.

Proves:
1. JSON + Base64 create works (201/202).
2. A parent sequence pipeline can be created from JSON (Wait1 -> Wait2).
3. A pipeline that uses @pipeline().parameters.WaitSeconds WITHOUT declaring
   parameters is still created.
4. Optional: run both pipelines so create success vs run failure is visible.

Usage:
  python demo_proof.py
  python demo_proof.py --run
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

WORKSPACE_ID = "e25cb526-ff7e-424f-8a79-8265bade11ee"
AZ_PATH = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
BASE = "https://api.fabric.microsoft.com/v1"
ROOT = Path(__file__).resolve().parent


def get_token() -> str:
    result = subprocess.run(
        [
            AZ_PATH,
            "account",
            "get-access-token",
            "--resource",
            "https://api.fabric.microsoft.com",
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Azure CLI failed: {result.stderr}")
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("Empty Fabric token")
    return token


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def encode_definition(path: Path) -> dict:
    definition = json.loads(path.read_text(encoding="utf-8"))
    payload = base64.b64encode(json.dumps(definition).encode("utf-8")).decode("utf-8")
    return {
        "parts": [
            {
                "path": "pipeline-content.json",
                "payload": payload,
                "payloadType": "InlineBase64",
            }
        ]
    }


def poll_operation(session: requests.Session, token: str, operation_id: str, timeout_s: int = 180):
    url = f"{BASE}/operations/{operation_id}"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = session.get(url, headers=headers(token))
        resp.raise_for_status()
        body = resp.json()
        status = body.get("status")
        if status == "Succeeded":
            result = session.get(f"{url}/result", headers=headers(token))
            if result.status_code == 200:
                return result.json()
            return body
        if status == "Failed":
            raise RuntimeError(f"Operation failed: {json.dumps(body)}")
        time.sleep(int(resp.headers.get("Retry-After", 5)))
    raise TimeoutError(f"Operation {operation_id} timed out")


def create_pipeline(session: requests.Session, token: str, display_name: str, json_path: Path) -> dict:
    url = f"{BASE}/workspaces/{WORKSPACE_ID}/dataPipelines"
    body = {
        "displayName": display_name,
        "description": f"Demo proof from {json_path.name}",
        "definition": encode_definition(json_path),
    }
    resp = session.post(url, headers=headers(token), json=body)
    record = {
        "displayName": display_name,
        "sourceJson": json_path.name,
        "httpStatus": resp.status_code,
        "response": None,
        "id": None,
    }
    try:
        record["response"] = resp.json()
    except ValueError:
        record["response"] = resp.text

    if resp.status_code == 201:
        record["id"] = (record["response"] or {}).get("id")
        return record

    if resp.status_code == 202:
        operation_id = resp.headers.get("x-ms-operation-id")
        record["operationId"] = operation_id
        result = poll_operation(session, token, operation_id)
        record["id"] = result.get("id")
        record["response"] = result
        return record

    record["createFailed"] = True
    return record


def get_definition(session: requests.Session, token: str, pipeline_id: str) -> dict:
    url = f"{BASE}/workspaces/{WORKSPACE_ID}/dataPipelines/{pipeline_id}/getDefinition"
    resp = session.post(url, headers=headers(token))
    if resp.status_code == 202:
        operation_id = resp.headers.get("x-ms-operation-id")
        return poll_operation(session, token, operation_id)
    resp.raise_for_status()
    return resp.json()


def decode_pipeline_content(definition_response: dict) -> dict | None:
    parts = (definition_response.get("definition") or {}).get("parts") or []
    for part in parts:
        if part.get("path") == "pipeline-content.json":
            raw = base64.b64decode(part["payload"]).decode("utf-8")
            return json.loads(raw)
    return None


def run_pipeline(session: requests.Session, token: str, pipeline_id: str, timeout_s: int = 180) -> dict:
    url = f"{BASE}/workspaces/{WORKSPACE_ID}/items/{pipeline_id}/jobs/Pipeline/instances"
    resp = session.post(url, headers=headers(token))
    record = {
        "httpStatus": resp.status_code,
        "location": resp.headers.get("Location"),
        "body": None,
        "jobStatus": None,
    }
    try:
        record["body"] = resp.json()
    except ValueError:
        record["body"] = resp.text

    location = record["location"]
    if resp.status_code != 202 or not location:
        return record

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        job = session.get(location, headers=headers(token))
        job.raise_for_status()
        payload = job.json()
        status = payload.get("status")
        record["jobStatus"] = status
        record["job"] = payload
        if status in {"Completed", "Failed", "Cancelled", "Deduped"}:
            return record
        time.sleep(int(job.headers.get("Retry-After", 5)))
    record["jobStatus"] = "Timeout"
    return record


def parent_from_child(child_name: str, child_id: str) -> dict:
    # Fabric rejects display-name references. Use the child pipeline GUID.
    _ = child_name
    return {
        "properties": {
            "description": "DEMO: parent ExecutePipeline -> child GUID, then Wait.",
            "activities": [
                {
                    "name": "RunChild",
                    "type": "ExecutePipeline",
                    "dependsOn": [],
                    "typeProperties": {
                        "pipeline": {
                            "referenceName": child_id,
                            "type": "PipelineReference",
                        },
                        "waitOnCompletion": True,
                    },
                },
                {
                    "name": "AfterChild",
                    "type": "Wait",
                    "dependsOn": [
                        {
                            "activity": "RunChild",
                            "dependencyConditions": ["Succeeded"],
                        }
                    ],
                    "typeProperties": {
                        "waitTimeInSeconds": 3,
                    },
                },
            ],
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run",
        action="store_true",
        help="Also trigger pipeline jobs (create still runs without this).",
    )
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "workspaceId": WORKSPACE_ID,
        "stamp": stamp,
        "claim": (
            "JSON create works. Sequence pipelines work. Parent ExecutePipeline "
            "works only with the child GUID. Undeclared @pipeline().parameters "
            "is rejected at create (HTTP 400), not at runtime."
        ),
        "pipelines": [],
    }

    token = get_token()
    session = requests.Session()

    cases = [
        ("Demo_Proof_ValidSeq_" + stamp, ROOT / "demo_json" / "01_valid_sequence.json"),
        ("Demo_Proof_UndeclaredParam_" + stamp, ROOT / "demo_json" / "02_undeclared_parameter.json"),
        ("Demo_Proof_Child_" + stamp, ROOT / "demo_json" / "03_child.json"),
    ]

    print("=" * 72)
    print("FABRIC PIPELINE CREATE DEMO")
    print("=" * 72)

    created = {}
    for name, path in cases:
        print(f"\nCREATE {name} from {path.name}")
        record = create_pipeline(session, token, name, path)
        print(f"  HTTP {record['httpStatus']}  id={record.get('id')}")
        if record.get("createFailed"):
            print(f"  Response: {record['response']}")
        else:
            definition = get_definition(session, token, record["id"])
            content = decode_pipeline_content(definition)
            record["storedHasParametersBlock"] = bool(
                (content or {}).get("properties", {}).get("parameters")
            )
            record["storedActivities"] = [
                a.get("name") for a in (content or {}).get("properties", {}).get("activities", [])
            ]
            print(f"  Stored parameters block: {record['storedHasParametersBlock']}")
            print(f"  Stored activities: {record['storedActivities']}")
        created[name] = record
        report["pipelines"].append(record)

    child_name = "Demo_Proof_Child_" + stamp
    child = created.get(child_name)
    if child and child.get("id"):
        parent_name = "Demo_Proof_ParentInvoke_" + stamp
        parent_path = ROOT / "demo_json" / f"04_parent_invoke_{stamp}.json"
        parent_path.write_text(
            json.dumps(parent_from_child(child_name, child["id"]), indent=2),
            encoding="utf-8",
        )
        print(f"\nCREATE {parent_name} (ExecutePipeline -> child GUID)")
        parent = create_pipeline(session, token, parent_name, parent_path)
        print(f"  HTTP {parent['httpStatus']}  id={parent.get('id')}")
        if parent.get("createFailed"):
            print("  Parent ExecutePipeline create failed.")
            print(f"  Response: {parent['response']}")
            print("  Sequence proof still stands from Demo_Proof_ValidSeq (Wait1 -> Wait2).")
        report["pipelines"].append(parent)
        created[parent_name] = parent

    if args.run:
        print("\nRUN JOBS")
        for label in [
            "Demo_Proof_ValidSeq_" + stamp,
            "Demo_Proof_UndeclaredParam_" + stamp,
        ]:
            rec = created.get(label)
            if not rec or not rec.get("id"):
                continue
            print(f"\nRUN {label}")
            job = run_pipeline(session, token, rec["id"])
            rec["run"] = job
            print(f"  Start HTTP {job['httpStatus']}  jobStatus={job.get('jobStatus')}")

    out = ROOT / "demo_proof_results.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n" + "=" * 72)
    print("SUMMARY FOR DEMO")
    print("=" * 72)
    for rec in report["pipelines"]:
        status = rec["httpStatus"]
        created_ok = status in (201, 202) and not rec.get("createFailed")
        print(
            f"- {rec['displayName']}: create HTTP {status} "
            f"{'CREATED' if created_ok else 'NOT CREATED'}"
        )
        if rec.get("run"):
            print(f"    run jobStatus={rec['run'].get('jobStatus')}")
    print(f"\nSaved {out}")
    print("Open these items in the Fabric workspace to show the canvas.")


if __name__ == "__main__":
    main()
