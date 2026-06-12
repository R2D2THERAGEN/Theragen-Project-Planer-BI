# Power BI Datasets (Semantic Models) API

Base: `https://api.powerbi.com/v1.0/myorg`

## Execute Queries (DAX)
```
POST /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/executeQueries
```
Body:
```json
{
  "queries": [
    { "query": "EVALUATE TOPN(10, Sales, Sales[Revenue], DESC)" }
  ],
  "serializerSettings": { "includeNulls": true },
  "impersonatedUserName": "user@company.com"
}
```
- `queries` — array, supports multiple queries per request
- `impersonatedUserName` — optional, test RLS as another user
- Response: `{ "results": [{ "tables": [{ "rows": [...] }] }] }`

## Refresh Dataset
```
POST /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/refreshes
```
Body:
```json
{
  "type": "Full",
  "commitMode": "transactional",
  "maxParallelism": 10,
  "retryCount": 3,
  "objects": [
    { "table": "Sales" },
    { "table": "Products", "partition": "2024" }
  ],
  "applyRefreshPolicy": true
}
```
Types: `Full`, `Automatic`, `DataOnly`, `Calculate`, `ClearValues`, `Defragment`
Returns `202` with request ID in `x-ms-request-id` header.

## Get Refresh History
```
GET /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/refreshes
GET /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/refreshes?$top=10
```
Response: `{ "value": [{ "requestId", "refreshType", "startTime", "endTime", "status", "serviceExceptionJson" }] }`

## Get Refresh Status
```
GET /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/refreshes/{refreshId}
```

## Cancel Refresh
```
DELETE /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/refreshes/{refreshId}
```

## Get Parameters
```
GET /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/parameters
```

## Update Parameters
```
POST /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/Default.UpdateParameters
```
Body: `{ "updateDetails": [{ "name": "ServerName", "newValue": "newserver.database.windows.net" }] }`

## Bind to Gateway
```
POST /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/Default.BindToGateway
```
Body: `{ "gatewayObjectId": "uuid", "datasourceObjectIds": ["uuid"] }`

## Take Over
```
POST /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/Default.TakeOver
```
No body. Transfers ownership to the calling user.

## Discover Gateways
```
GET /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/Default.DiscoverGateways
```

## Get Datasources
```
GET /v1.0/myorg/groups/{groupId}/datasets/{datasetId}/datasources
```
