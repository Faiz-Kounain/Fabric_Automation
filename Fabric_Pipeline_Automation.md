# Microsoft Fabric Pipeline Automation – Overview

## Objective

Automate the creation of Microsoft Fabric Data Pipelines from VS Code using Python and the Fabric REST API.

## High-Level Flow

```
VS Code
   ↓
Python Script
   ↓
Azure CLI Authentication
   ↓
Fabric Access Token
   ↓
Fabric REST API
   ↓
Create Fabric Data Pipeline
```

## Setup Steps

### 1. Create Project

Create a project folder in VS Code:

```
project_poc/
├── create_pipeline.py
└── pipeline.json
```

### 2. Install Azure CLI

Install Azure CLI on Windows:

```powershell
winget install --exact --id Microsoft.AzureCLI
```

Verify:

```powershell
az --version
```

### 3. Authenticate

Log in using Azure CLI:

```powershell
az login --allow-no-subscriptions
```

### 4. Get Fabric Access Token

```powershell
az account get-access-token `
    --resource https://api.fabric.microsoft.com `
    --query accessToken `
    -o tsv
```

### 5. Install Python Package

```powershell
pip install requests
```

### 6. Prepare Pipeline Definition

Create the pipeline definition in JSON.

Example:

```json
{
  "properties": {
    "activities": [
      {
        "name": "Wait10Seconds",
        "type": "Wait",
        "dependsOn": [],
        "typeProperties": {
          "waitTimeInSeconds": 10
        }
      }
    ]
  }
}
```

### 7. Get Fabric Workspace ID

Get the workspace ID from the Fabric workspace URL:

```
https://app.fabric.microsoft.com/groups/<WORKSPACE_ID>/...
```

### 8. Create Pipeline Using REST API

Python uses the Fabric REST API:

```http
POST https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/dataPipelines
```

The Python script:

1. Gets the Fabric access token.
2. Reads the pipeline JSON.
3. Encodes the pipeline definition.
4. Sends the request to the Fabric REST API.
5. Creates the pipeline in the Fabric workspace.

### 9. Run from VS Code

```powershell
python create_pipeline.py
```

The pipeline is then created automatically in Microsoft Fabric.

## Future Goal

The same approach can be extended for DataStage migration:

```
DataStage DSX
     ↓
Parse Jobs & Dependencies
     ↓
Generate Fabric Pipeline JSON
     ↓
Python Automation
     ↓
Fabric REST API
     ↓
Fabric Pipelines
```

This will allow DataStage orchestration to be converted and created in Microsoft Fabric programmatically.
