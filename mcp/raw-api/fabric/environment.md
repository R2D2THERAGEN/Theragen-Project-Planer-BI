# Environment API

Base: `https://api.fabric.microsoft.com/v1`

Environments manage Spark compute configs: custom Python/R libraries, Spark properties, and runtime version.

## Standard CRUD
```
List:    GET    /v1/workspaces/{workspaceId}/environments
Create:  POST   /v1/workspaces/{workspaceId}/environments
Get:     GET    /v1/workspaces/{workspaceId}/environments/{environmentId}
Update:  PATCH  /v1/workspaces/{workspaceId}/environments/{environmentId}
Delete:  DELETE /v1/workspaces/{workspaceId}/environments/{environmentId}
```

### Create Body
```json
{
  "displayName": "ml-environment",
  "description": "ML libraries for training"
}
```

## Get Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/environments/{environmentId}/getDefinition
```
Response parts include:
- `environment.yml` — runtime version, Spark properties
- `requirements.txt` — pip packages
- `conda.yml` — conda packages
- Custom wheel files and JARs

## Update Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/environments/{environmentId}/updateDefinition
```
Body:
```json
{
  "definition": {
    "parts": [
      {
        "path": "environment.yml",
        "payload": "base64-encoded-yaml",
        "payloadType": "InlineBase64"
      }
    ]
  }
}
```

## Publish Environment (LRO)
```
POST /v1/workspaces/{workspaceId}/environments/{environmentId}/staging/publish
```
No body. Applies staged library changes to the Spark pool.
This is the key operation — after updating definition, you must publish.

## Cancel Publish
```
POST /v1/workspaces/{workspaceId}/environments/{environmentId}/staging/cancelPublish
```

## Staging Libraries

### Upload Library
```
POST /v1/workspaces/{workspaceId}/environments/{environmentId}/staging/libraries
```
Content-Type: `multipart/form-data`
Upload `.whl`, `.jar`, `.tar.gz` files.

### Delete Library
```
DELETE /v1/workspaces/{workspaceId}/environments/{environmentId}/staging/libraries?libraryToDelete={filename}
```

### Get Published Libraries
```
GET /v1/workspaces/{workspaceId}/environments/{environmentId}/libraries
```

### Get Staging Libraries
```
GET /v1/workspaces/{workspaceId}/environments/{environmentId}/staging/libraries
```

## Spark Settings

### Get Spark Settings
```
GET /v1/workspaces/{workspaceId}/environments/{environmentId}/sparkcompute
```

### Update Spark Settings
```
PATCH /v1/workspaces/{workspaceId}/environments/{environmentId}/sparkcompute
```
Body:
```json
{
  "instancePool": {
    "name": "starterPool",
    "type": "Workspace"
  },
  "driverCores": 4,
  "driverMemory": "28g",
  "executorCores": 4,
  "executorMemory": "28g",
  "dynamicExecutorAllocation": {
    "enabled": true,
    "minExecutors": 1,
    "maxExecutors": 10
  },
  "runtimeVersion": "1.3"
}
```

## Typical Workflow (replace broken install_requirements)

1. Create or Get environment
2. Update definition with `requirements.txt` (pip packages)
3. Publish: `POST .../staging/publish`
4. Poll LRO until published
5. Attach environment to notebook/workspace

## Permissions
- Scope: `Environment.ReadWrite.All`
- Create/Update/Delete: workspace Contributor+
