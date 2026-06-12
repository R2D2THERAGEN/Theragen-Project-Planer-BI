# Notebook API

Base: `https://api.fabric.microsoft.com/v1`

## Standard CRUD
```
List:    GET    /v1/workspaces/{workspaceId}/notebooks
Create:  POST   /v1/workspaces/{workspaceId}/notebooks  (LRO)
Get:     GET    /v1/workspaces/{workspaceId}/notebooks/{notebookId}
Update:  PATCH  /v1/workspaces/{workspaceId}/notebooks/{notebookId}
Delete:  DELETE /v1/workspaces/{workspaceId}/notebooks/{notebookId}
```

### Create Body
```json
{ "displayName": "ETL Pipeline", "description": "Daily ETL" }
```

## Get Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/notebooks/{notebookId}/getDefinition
POST /v1/workspaces/{workspaceId}/notebooks/{notebookId}/getDefinition?format=ipynb
```
Format: `ipynb` (default) returns Jupyter notebook JSON.
Response: `{ "definition": { "parts": [{ "path": "notebook-content.py", "payload": "base64...", "payloadType": "InlineBase64" }] } }`

## Update Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/notebooks/{notebookId}/updateDefinition
```
Body: same structure as Get Definition response.

## Permissions
- Scope: `Notebook.ReadWrite.All` or `Item.ReadWrite.All`
