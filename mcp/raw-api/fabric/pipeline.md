# Data Pipeline API

Base: `https://api.fabric.microsoft.com/v1`

## Standard CRUD
```
List:    GET    /v1/workspaces/{workspaceId}/dataPipelines
Create:  POST   /v1/workspaces/{workspaceId}/dataPipelines
Get:     GET    /v1/workspaces/{workspaceId}/dataPipelines/{dataPipelineId}
Update:  PATCH  /v1/workspaces/{workspaceId}/dataPipelines/{dataPipelineId}
Delete:  DELETE /v1/workspaces/{workspaceId}/dataPipelines/{dataPipelineId}
```

## Get/Update Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/dataPipelines/{dataPipelineId}/getDefinition
POST /v1/workspaces/{workspaceId}/dataPipelines/{dataPipelineId}/updateDefinition
```
Definition contains pipeline JSON (activities, linked services, parameters).

## Run Pipeline (via Job Scheduler)
```
POST /v1/workspaces/{workspaceId}/items/{pipelineId}/jobs/instances?jobType=Pipeline
```
Body (with parameters):
```json
{
  "executionData": {
    "parameters": {
      "param1": "value1"
    }
  }
}
```

## Permissions
- Scope: `DataPipeline.ReadWrite.All` or `Item.ReadWrite.All`
