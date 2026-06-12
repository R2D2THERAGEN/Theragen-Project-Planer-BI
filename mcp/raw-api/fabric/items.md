# Items (Generic) API

Base: `https://api.fabric.microsoft.com/v1`

Generic item operations work across ALL supported Fabric item types.

## List Items
```
GET /v1/workspaces/{workspaceId}/items
GET /v1/workspaces/{workspaceId}/items?type={ItemType}&continuationToken={token}
```
Query params:
- `type` — filter by item type (e.g., `Notebook`, `SemanticModel`)
- `continuationToken` — pagination

Response: `{ "value": [{ "id", "type", "displayName", "description", "workspaceId", "folderId" }] }`

## Create Item
```
POST /v1/workspaces/{workspaceId}/items
```
Body:
```json
{
  "type": "Notebook",
  "displayName": "My Item",
  "description": "optional",
  "folderId": "uuid (optional)",
  "definition": {
    "parts": [
      {
        "path": "notebook-content.py",
        "payload": "base64-encoded-content",
        "payloadType": "InlineBase64"
      }
    ]
  }
}
```
Use either `definition` or `creationPayload`, never both.
Supported types: see `_index.md` for full list.

## Get Item
```
GET /v1/workspaces/{workspaceId}/items/{itemId}
```

## Update Item
```
PATCH /v1/workspaces/{workspaceId}/items/{itemId}
```
Body: `{ "displayName": "New Name", "description": "Updated desc" }`

## Delete Item
```
DELETE /v1/workspaces/{workspaceId}/items/{itemId}
```

## Get Item Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/items/{itemId}/getDefinition
POST /v1/workspaces/{workspaceId}/items/{itemId}/getDefinition?format={format}
```
Query params:
- `format` — optional format hint (e.g., `ipynb` for notebooks, `TMDL` for semantic models)

Response (200 or 202):
```json
{
  "definition": {
    "parts": [
      { "path": "notebook-content.py", "payload": "base64...", "payloadType": "InlineBase64" }
    ]
  }
}
```

## Update Item Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/items/{itemId}/updateDefinition
POST /v1/workspaces/{workspaceId}/items/{itemId}/updateDefinition?updateMetadata=true
```
Body:
```json
{
  "definition": {
    "parts": [
      {
        "path": "notebook-content.py",
        "payload": "base64-content",
        "payloadType": "InlineBase64"
      }
    ]
  }
}
```

## Move Item
```
POST /v1/workspaces/{workspaceId}/items/{itemId}/move
```
Body: `{ "targetWorkspaceId": "uuid" }`

## Bulk Move Items
```
POST /v1/workspaces/{workspaceId}/items/bulkMove
```
Body: `{ "targetWorkspaceId": "uuid", "items": [{ "id": "uuid" }] }`

## List Item Connections
```
GET /v1/workspaces/{workspaceId}/items/{itemId}/connections
```

## Permissions
- Scope: `Item.ReadWrite.All` or `{ItemType}.ReadWrite.All`
- Create/Update/Delete require workspace Contributor+
