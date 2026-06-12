# Semantic Model API

Base: `https://api.fabric.microsoft.com/v1`

## Standard CRUD
```
List:    GET    /v1/workspaces/{workspaceId}/semanticModels
Create:  POST   /v1/workspaces/{workspaceId}/semanticModels  (LRO)
Get:     GET    /v1/workspaces/{workspaceId}/semanticModels/{semanticModelId}
Update:  PATCH  /v1/workspaces/{workspaceId}/semanticModels/{semanticModelId}
Delete:  DELETE /v1/workspaces/{workspaceId}/semanticModels/{semanticModelId}
```

## Get Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/semanticModels/{semanticModelId}/getDefinition
POST /v1/workspaces/{workspaceId}/semanticModels/{semanticModelId}/getDefinition?format=TMDL
```
Formats: `TMSL` (default, single model.bim), `TMDL` (folder-based, multiple files)
Response parts for TMSL: `{ "definition": { "parts": [{ "path": "model.bim", "payload": "base64...", "payloadType": "InlineBase64" }] } }`
Response parts for TMDL: multiple parts like `definition/tables/Sales.tmdl`, `definition/model.tmdl`, etc.

Note: Only works with user-created semantic models. Auto-generated lakehouse default models return error.

## Update Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/semanticModels/{semanticModelId}/updateDefinition
```
Body: same structure as Get Definition response.

## Permissions
- Scope: `SemanticModel.ReadWrite.All` or `Dataset.ReadWrite.All`
- Get Definition only works on models the user owns or has Build permission on
