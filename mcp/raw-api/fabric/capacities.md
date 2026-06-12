# Capacities API

Base: `https://api.fabric.microsoft.com/v1`

## List Capacities
```
GET /v1/capacities
GET /v1/capacities?continuationToken={token}
```
Response:
```json
{
  "value": [
    {
      "id": "uuid",
      "displayName": "My F64 Capacity",
      "sku": "F64",
      "region": "westeurope",
      "state": "Active"
    }
  ]
}
```
States: `Active`, `Inactive`, `Provisioning`, `UpdatingSku`, `Deleting`
SKUs: F2, F4, F8, F16, F32, F64, F128, F256, F512, F1024, F2048 (Fabric), P1-P5 (Power BI Premium)

## Permissions
- Scope: `Capacity.Read.All` or `Capacity.ReadWrite.All`
- Returns only capacities the caller has access to
