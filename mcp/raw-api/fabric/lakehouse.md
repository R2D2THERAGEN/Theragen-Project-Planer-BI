# Lakehouse API

Base: `https://api.fabric.microsoft.com/v1`

## Standard CRUD

```
List:    GET    /v1/workspaces/{workspaceId}/lakehouses
Create:  POST   /v1/workspaces/{workspaceId}/lakehouses
Get:     GET    /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}
Update:  PATCH  /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}
Delete:  DELETE /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}
```

### Create Body
```json
{
  "displayName": "sales_lakehouse",
  "description": "Sales data",
  "creationPayload": {
    "enableSchemas": true
  }
}
```
Use `enableSchemas: true` for schema-enabled lakehouses.

### Get Response (includes properties)
```json
{
  "id": "uuid",
  "displayName": "sales_lakehouse",
  "type": "Lakehouse",
  "properties": {
    "oneLakeFilesPath": "https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{lakehouseId}/Files",
    "oneLakeTablesPath": "https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{lakehouseId}/Tables",
    "sqlEndpointProperties": {
      "id": "uuid",
      "connectionString": "...",
      "provisioningStatus": "Success"
    }
  }
}
```

## List Tables
```
GET /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/tables
GET /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/tables?continuationToken={token}&maxResults={max}
```
Response: `{ "data": [{ "name", "type", "location", "format" }] }`

## Load Table (server-side)
```
POST /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/tables/{tableName}/load
```
Body:
```json
{
  "relativePath": "Files/sales/2024.csv",
  "pathType": "File",
  "mode": "Overwrite",
  "formatOptions": {
    "format": "Csv",
    "header": true,
    "delimiter": ","
  }
}
```
Modes: `Overwrite`, `Append`
Formats: `Csv`, `Parquet`
Path types: `File`, `Folder`
`relativePath` is relative to the lakehouse root (Files/ or Tables/).
LRO — returns 202.

## Table Maintenance (Background Job)
```
POST /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/instances?jobType=TableMaintenance
```
Body:
```json
{
  "executionData": {
    "tableName": "sales_data",
    "schemaName": "dbo",
    "optimizeSettings": {
      "vOrder": true,
      "zOrderBy": ["date", "region"]
    },
    "vacuumSettings": {
      "retentionPeriod": "7.00:00:00"
    }
  }
}
```
Key options:
- `vOrder` — V-Order compaction (not available via client-side delta-rs)
- `zOrderBy` — Z-Order columns
- `schemaName` — required for schema-enabled lakehouses
- `retentionPeriod` — timespan format (days.hours:minutes:seconds)

## Get/Update Definition (LRO)
```
POST /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/getDefinition
POST /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/updateDefinition
```
Definition parts may include: shortcuts, data-access-roles, alm-settings.

## SQL Endpoint Metadata Sync
```
POST /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/sqlEndpoint/sync
```
Triggers SQL endpoint to refresh its metadata (pick up new tables).

## Permissions
- List/Get: `Lakehouse.Read.All` or `Lakehouse.ReadWrite.All`
- Create/Update/Delete: `Lakehouse.ReadWrite.All` + workspace Contributor+
- Load Table: workspace Contributor+
