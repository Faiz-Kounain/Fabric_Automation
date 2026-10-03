import subprocess
import requests
import time


WORKSPACE_ID = "e25cb526-ff7e-424f-8a79-8265bade11ee"

PARENT_PIPELINE_ID = "63f7be4b-57af-4d7a-918e-236dce0fd676"

AZ_PATH = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

BASE = "https://api.fabric.microsoft.com/v1"


def get_token():

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
            "tsv"
        ],
        capture_output=True,
        text=True
    )

    return result.stdout.strip()


def run_pipeline(token):

    url = (
        f"{BASE}/workspaces/{WORKSPACE_ID}"
        f"/dataPipelines/{PARENT_PIPELINE_ID}"
        f"/jobs/execute/instances"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        headers=headers
    )

    print("RUN HTTP STATUS:", response.status_code)
    print("RUN RESPONSE:", response.text)
    print()

    return response


print("Getting Azure token...")

token = get_token()

print("Token received:", bool(token))
print("Token length:", len(token))
print()

response = run_pipeline(token)

if response.status_code == 202:

    print("PIPELINE RUN STARTED SUCCESSFULLY")

    location = response.headers.get("Location")

    print("Location:")
    print(location)

else:

    print("PIPELINE RUN FAILED")