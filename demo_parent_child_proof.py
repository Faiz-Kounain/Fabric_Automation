import base64
import json
import subprocess
from datetime import datetime

import requests


# ==================================================
# CONFIGURATION
# ==================================================

WORKSPACE_ID = "e25cb526-ff7e-424f-8a79-8265bade11ee"

BASE = "https://api.fabric.microsoft.com/v1"

AZ_PATH = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

CHILD_1_NAME = f"Demo_Child_1_{suffix}"
CHILD_2_NAME = f"Demo_Child_2_{suffix}"
PARENT_NAME = f"Demo_Parent_{suffix}"


# ==================================================
# GET AZURE TOKEN
# ==================================================

def get_token():

    print("Getting Azure token...")

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

    print("Azure CLI return code:", result.returncode)

    token = result.stdout.strip()

    print("Token received:", bool(token))
    print("Token length:", len(token))

    if not token:
        print("ERROR:")
        print(result.stderr)
        raise Exception("Could not get Azure token")

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

def create_pipeline(token, pipeline_name, definition):

    print("\n" + "=" * 50)
    print("CREATING:", pipeline_name)
    print("=" * 50)

    definition_json = json.dumps(definition)

    payload_base64 = base64.b64encode(
        definition_json.encode("utf-8")
    ).decode("utf-8")

    body = {

        "displayName": pipeline_name,

        "description":
            "Parent Child Orchestration POC",

        "definition": {

            "parts": [

                {

                    "path":
                        "pipeline-content.json",

                    "payload":
                        payload_base64,

                    "payloadType":
                        "InlineBase64"
                }

            ]
        }
    }

    url = (
        f"{BASE}/workspaces/"
        f"{WORKSPACE_ID}/dataPipelines"
    )

    response = requests.post(
        url,
        headers=get_headers(token),
        json=body
    )

    print("CREATE HTTP STATUS:", response.status_code)
    print("CREATE RESPONSE:", response.text)

    if response.status_code == 201:

        print("CREATE SUCCESS:", pipeline_name)

        return response.json()

    else:

        print("CREATE FAILED:", pipeline_name)

        return None


# ==================================================
# CHILD PIPELINE DEFINITION
# ==================================================

def child_pipeline_definition(child_number):

    return {

        "properties": {

            "description":
                f"Child Pipeline {child_number} - Parent Child POC",

            "activities": [

                {

                    "name":
                        f"Wait_Child_{child_number}",

                    "type":
                        "Wait",

                    "dependsOn": [],

                    "typeProperties": {

                        "waitTimeInSeconds":
                            5
                    }
                }

            ]
        }
    }


# ==================================================
# PARENT PIPELINE DEFINITION
# ==================================================

def parent_pipeline_definition(child1_name, child2_name):

    return {

        "properties": {

            "description":
                "Parent pipeline executing two child pipelines",

            "activities": [

                {

                    "name":
                        "Execute_Child_1",

                    "type":
                        "ExecutePipeline",

                    "dependsOn": [],

                    "typeProperties": {

                        "pipeline": {

                            "referenceName":
                                child1_name,

                            "type":
                                "PipelineReference"
                        },

                        "waitOnCompletion":
                            True
                    }
                },

                {

                    "name":
                        "Execute_Child_2",

                    "type":
                        "ExecutePipeline",

                    "dependsOn": [

                        {

                            "activity":
                                "Execute_Child_1",

                            "dependencyConditions": [

                                "Succeeded"
                            ]
                        }

                    ],

                    "typeProperties": {

                        "pipeline": {

                            "referenceName":
                                child2_name,

                            "type":
                                "PipelineReference"
                        },

                        "waitOnCompletion":
                            True
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

    # ----------------------------------------------
    # STEP 1
    # CREATE CHILD 1
    # ----------------------------------------------

    child1 = create_pipeline(

        token,

        CHILD_1_NAME,

        child_pipeline_definition(1)
    )

    if not child1:

        print("\nSTOPPING - Child 1 creation failed.")

        return


    # ----------------------------------------------
    # STEP 2
    # CREATE CHILD 2
    # ----------------------------------------------

    child2 = create_pipeline(

        token,

        CHILD_2_NAME,

        child_pipeline_definition(2)
    )

    if not child2:

        print("\nSTOPPING - Child 2 creation failed.")

        return


    # ----------------------------------------------
    # STEP 3
    # CREATE PARENT
    # ----------------------------------------------

    parent = create_pipeline(

        token,

        PARENT_NAME,

        parent_pipeline_definition(
            child1["id"],
            child2["id"]
        )
    )

    if not parent:

        print("\nPARENT CREATION FAILED.")

        return


    # ----------------------------------------------
    # FINAL RESULT
    # ----------------------------------------------

    print("\n")
    print("=" * 60)
    print("PARENT / CHILD CREATION POC RESULT")
    print("=" * 60)

    print("Child 1 :", CHILD_1_NAME)
    print("Child 2 :", CHILD_2_NAME)
    print("Parent  :", PARENT_NAME)

    print("\nSUCCESS:")
    print("Child pipelines were created.")
    print("Parent pipeline was created with ExecutePipeline references.")

    print("\nNEXT STEP:")
    print("Execution will be tested separately.")


if __name__ == "__main__":

    main()