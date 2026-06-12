# Long Running Operations (LRO)

Base: `https://api.fabric.microsoft.com/v1`

Many Fabric APIs return `202 Accepted` for async operations. Use these endpoints to poll status.

## Get Operation State
```
GET /v1/operations/{operationId}
```
Response:
```json
{
  "id": "uuid",
  "status": "Running",
  "createdTimeUtc": "2026-03-10T08:00:00Z",
  "lastUpdatedTimeUtc": "2026-03-10T08:05:00Z",
  "percentComplete": 50,
  "error": null
}
```
Statuses: `NotStarted`, `Running`, `Succeeded`, `Failed`, `Undefined`

## Get Operation Result
```
GET /v1/operations/{operationId}/result
```
Returns the operation's result payload (varies by operation type).
Only available when status = `Succeeded`.

## Polling Pattern

1. API returns `202` with `Location` and `x-ms-operation-id` headers
2. Extract `operationId` from `x-ms-operation-id` header
3. Poll: `GET /v1/operations/{operationId}`
4. Wait `Retry-After` seconds between polls
5. When `status` = `Succeeded`, optionally `GET .../result`
6. When `status` = `Failed`, check `error` field

## Common LRO Operations
- Git: Commit, Update from Git, Initialize, Get Status
- Items: Create (some types), Get Definition, Update Definition
- Deployment Pipelines: Deploy Stage Content
- Environments: Publish
- Lakehouse: Create, Load Table, Table Maintenance
