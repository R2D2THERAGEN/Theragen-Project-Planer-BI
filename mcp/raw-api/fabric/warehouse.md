# Warehouse API

Base: `https://api.fabric.microsoft.com/v1`

## Standard CRUD
```
List:    GET    /v1/workspaces/{workspaceId}/warehouses
Create:  POST   /v1/workspaces/{workspaceId}/warehouses  (LRO)
Get:     GET    /v1/workspaces/{workspaceId}/warehouses/{warehouseId}
Update:  PATCH  /v1/workspaces/{workspaceId}/warehouses/{warehouseId}
Delete:  DELETE /v1/workspaces/{workspaceId}/warehouses/{warehouseId}
```

### Create Body
```json
{ "displayName": "sales_warehouse", "description": "Central warehouse" }
```

### Get Response (includes connection string)
```json
{
  "id": "uuid",
  "displayName": "sales_warehouse",
  "properties": {
    "connectionString": "...",
    "createdDate": "2026-03-10T08:00:00Z",
    "lastUpdatedTime": "2026-03-10T08:00:00Z"
  }
}
```

## Permissions
- Scope: `Warehouse.ReadWrite.All` or `Warehouse.Read.All`
