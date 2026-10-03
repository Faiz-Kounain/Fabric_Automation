import subprocess
import requests
import base64
import json
import time
from datetime import datetime

suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
# ==================================================
# CONFIGURATION
# ==================================================

workspace_id = "e25cb526-ff7e-424f-8a79-8265bade11ee"

az_path = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

BASE = "https://api.fabric.microsoft.com/v1"

headers_template = {
    "Content-Type": "application/json"
}


# ==================================================
# GET FABRIC TOKEN
# ==================================================

def get_token():

    print("Getting Azure token...")

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

    if result.stderr:
        print("Azure CLI error:", result.stderr)

    token = result.stdout.strip()

    print("Token received:", bool(token))
    print("Token length:", len(token))

    if not token:
        raise Exception("Could not get Fabric access token")

    return token


# ==================================================
# HEADERS
# ==================================================

def get_headers(token):

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


# ==================================================
# CREATE PIPELINE
# ==================================================

def create_pipeline(session, token, name, definition):

    print("\n========================================")
    print("CREATING:", name)
    print("========================================")

    pipeline_json = json.dumps(definition)

    encoded_definition = base64.b64encode(
        pipeline_json.encode("utf-8")
    ).decode("utf-8")

    body = {
        "displayName": name,
        "description": "Parameter validation POC",
        "definition": {
            "parts": [
                {
                    "path": "pipeline-content.json",
                    "payload": encoded_definition,
                    "payloadType": "InlineBase64"
                }
            ]
        }
    }

    url = (
        f"{BASE}/workspaces/"
        f"{workspace_id}/dataPipelines"
    )

    response = session.post(
        url,
        headers=get_headers(token),
        json=body
    )

    print("CREATE HTTP STATUS:", response.status_code)
    print("CREATE RESPONSE:", response.text)

    if response.status_code not in [200, 201, 202]:

        return {
            "created": False,
            "status_code": response.status_code,
            "response": response.text
        }

    result = response.json()

    return {
        "created": True,
        "status_code": response.status_code,
        "id": result.get("id"),
        "response": result
    }


# ==================================================
# RUN PIPELINE
# ==================================================

def run_pipeline(session, token, pipeline_id, parameters=None):

    print("\n----------------------------------------")
    print("RUNNING PIPELINE")
    print("----------------------------------------")

    url = (
        f"{BASE}/workspaces/"
        f"{workspace_id}/dataPipelines/"
        f"{pipeline_id}/jobs/instances"
    )

    body = {}

    if parameters is not None:
        body["executionData"] = {
            "parameters": parameters
        }

    response = session.post(
        url,
        headers=get_headers(token),
        json=body
    )

    print("RUN HTTP STATUS:", response.status_code)
    print("RUN RESPONSE:", response.text)

    if response.status_code not in [200, 201, 202]:

        return {
            "started": False,
            "status_code": response.status_code,
            "response": response.text
        }

    try:
        result = response.json()
    except ValueError:
        result = {}

    return {
        "started": True,
        "status_code": response.status_code,
        "response": result
    }


# ==================================================
# TEST 1
# DECLARED PARAMETER
# ==================================================

def declared_parameter_definition():

    return {

        "properties": {

            "description":
                "TEST 1 - parameter is declared and used",

            "parameters": {

                "wait_seconds": {

                    "type": "Int",

                    "defaultValue":
                        5
                }
            },

            "activities": [

                {

                    "name": "Wait_Declared_Parameter",

                    "type": "Wait",

                    "dependsOn": [],

                    "typeProperties": {

                        "waitTimeInSeconds":
                            "@pipeline().parameters.wait_seconds"
                    }
                }

            ]
        }
    }


# ==================================================
# TEST 2
# UNDECLARED PARAMETER
# ==================================================

def declared_parameter_not_used_definition():

    return {

        "properties": {

            "description":
                "TEST 2 - parameter is declared but NOT used",

            "parameters": {

                "wait_seconds": {

                    "type": "Int",

                    "defaultValue":
                        5
                }
            },

            "activities": [

                {

                    "name": "Wait_No_Parameter",

                    "type": "Wait",

                    "dependsOn": [],

                    "typeProperties": {

                        "waitTimeInSeconds": 5
                    }
                }

            ]
        }
    }


# ==================================================
# TEST 3
# UNDECLARED PARAMETER ACTUALLY USED
# ==================================================

def undeclared_parameter_used_definition():

    return {

        "properties": {

            "description":
                "TEST 3 - references undeclared parameter",

            "activities": [

                {

                    "name": "Wait_Undeclared_Parameter",

                    "type": "Wait",

                    "dependsOn": [],

                    "typeProperties": {

                        "waitTimeInSeconds": "@pipeline().parameters.table_name"
                    }
                }

            ]
        }
    }


# ==================================================
# MAIN
# ==================================================

def main():

    token = get_token()

    session = requests.Session()

    # ------------------------------------------------
    # TEST 1
    # ------------------------------------------------

    test1_name = f"Demo_Parameter_Declared_{suffix}"

    test1 = create_pipeline(
        session,
        token,
        test1_name,
        declared_parameter_definition()
    )

    if test1["created"]:

        print("\nTEST 1 CREATE: SUCCESS")

        pipeline_id = test1["id"]

        run_result = run_pipeline(
            session,
            token,
            pipeline_id,
            {
                "table_name":
                    "publicholidays_test"
            }
        )

        print(
            "\nTEST 1 RUN RESULT:",
            run_result
        )

    else:

        print("\nTEST 1 CREATE: FAILED")


    # ------------------------------------------------
    # TEST 2
    # ------------------------------------------------

    test2_name = f"Demo_Parameter_NotUsed_{suffix}"

    test2 = create_pipeline(
        session,
        token,
        test2_name,
        declared_parameter_not_used_definition()
    )

    if test2["created"]:

        print("\nTEST 2 CREATE: SUCCESS")

        pipeline_id = test2["id"]

        run_result = run_pipeline(
            session,
            token,
            pipeline_id
        )

        print(
            "\nTEST 2 RUN RESULT:",
            run_result
        )

    else:

        print("\nTEST 2 CREATE: FAILED")


    # ------------------------------------------------
    # TEST 3
    # ------------------------------------------------

    test3_name = f"Demo_Parameter_Undeclared_{suffix}"

    test3 = create_pipeline(
        session,
        token,
        test3_name,
        undeclared_parameter_used_definition()
    )

    if test3["created"]:

        print("\nTEST 3 CREATE: SUCCESS")

        pipeline_id = test3["id"]

        run_result = run_pipeline(
            session,
            token,
            pipeline_id
        )

        print(
            "\nTEST 3 RUN RESULT:",
            run_result
        )

    else:

        print("\nTEST 3 CREATE: FAILED")


    # ------------------------------------------------
    # SUMMARY
    # ------------------------------------------------

    print("\n")
    print("========================================")
    print("PARAMETER POC COMPLETED")
    print("========================================")

    print("""
TEST 1:
Declared parameter
    @pipeline().parameters.table_name

TEST 2:
No parameter reference

TEST 3:
Undeclared parameter
    @pipeline().parameters.table_name

Check the CREATE and RUN results above.
""")


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":
    main()