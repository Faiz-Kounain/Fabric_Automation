
import json
import base64
import subprocess
import requests

# Replace with your actual Fabric workspace ID
workspace_id = "e25cb526-ff7e-424f-8a79-8265bade11ee"
pipeline_id= "44ff5e56-81b5-4d08-989b-4de3e27d8405"
print("Getting Azure token...")

az_path = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

# Get a Microsoft Fabric access token
result = subprocess.run(
    [
        az_path,
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

print("Azure CLI return code:", result.returncode)
print("Azure CLI error:", result.stderr)

if result.returncode != 0:
    raise Exception("Azure CLI failed")

token = result.stdout.strip()

print("Token received:", bool(token))
print("Token length:", len(token))

# Read the pipeline definition
with open("pipeline.json", "r", encoding="utf-8") as file:
    pipeline_definition = json.load(file)

# Convert JSON into Base64
encoded_payload = base64.b64encode(
    json.dumps(pipeline_definition).encode("utf-8")
).decode("utf-8")

# Fabric REST API endpoint
url = (
    f"https://api.fabric.microsoft.com/v1/workspaces/"
    f"{workspace_id}/dataPipelines/"
    f"{pipeline_id}/updateDefinition"
)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

body = {
    # "displayName": "VSCode_Auto_Pipeline",
    # "description": "Created from VS Code using Python",
    "definition": {
        "parts": [
            {
                "path": "pipeline-content.json",
                "payload": encoded_payload,
                "payloadType": "InlineBase64"
            }
        ]
    }
}

# Create the pipeline in Fabric
response = requests.post(
    url,
    headers=headers,
    json=body
)

print("HTTP Status:", response.status_code)
print("Response:", response.text)

response.raise_for_status()
print("Pipeline creation request succeeded.")