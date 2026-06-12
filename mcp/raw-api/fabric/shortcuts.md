# OneLake Shortcuts API

Base: `https://api.fabric.microsoft.com/v1`

## Create Shortcut
```
POST /v1/workspaces/{workspaceId}/items/{itemId}/shortcuts
```
Body (OneLake target):
```json
{
  "name": "sales_data",
  "path": "Tables",
  "target": {
    "oneLake": {
      "workspaceId": "source-workspace-uuid",
      "itemId": "source-lakehouse-uuid",
      "path": "Tables/sales"
    }
  }
}
```

Body (ADLS Gen2 target):
```json
{
  "name": "external_data",
  "path": "Files",
  "target": {
    "adlsGen2": {
      "location": "https://mystorageaccount.dfs.core.windows.net",
      "subpath": "/container/folder",
      "connectionId": "uuid"
    }
  }
}
```

Body (Amazon S3 target):
```json
{
  "name": "s3_data",
  "path": "Files",
  "target": {
    "amazonS3": {
      "location": "https://mybucket.s3.amazonaws.com",
      "subpath": "/prefix",
      "connectionId": "uuid"
    }
  }
}
```

Supported targets: `oneLake`, `adlsGen2`, `amazonS3`, `s3Compatible`, `googleCloudStorage`, `dataverse`

## Get Shortcut
```
GET /v1/workspaces/{workspaceId}/items/{itemId}/shortcuts/{shortcutPath}/{shortcutName}
```

## List Shortcuts
```
GET /v1/workspaces/{workspaceId}/items/{itemId}/shortcuts
```

## Delete Shortcut
```
DELETE /v1/workspaces/{workspaceId}/items/{itemId}/shortcuts/{shortcutPath}/{shortcutName}
```

## Bulk Create Shortcuts
```
POST /v1/workspaces/{workspaceId}/items/{itemId}/shortcuts/bulk
```
Body: `{ "shortcuts": [ ...array of shortcut objects... ] }`

## Permissions
- Scope: `OneLake.ReadWrite.All`
- Contributor+ on the target item
