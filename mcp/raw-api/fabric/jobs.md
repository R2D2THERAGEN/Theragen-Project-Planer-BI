# Job Scheduler API

Base: `https://api.fabric.microsoft.com/v1`

Works across all item types that support jobs (notebooks, pipelines, semantic models, etc).

## Run On Demand Job
```
POST /v1/workspaces/{workspaceId}/items/{itemId}/jobs/instances?jobType={jobType}
```
Job types: `DefaultJob`, `TableMaintenance`, `RefreshMaterializeLakeViews`
Body (varies by job type):
```json
{
  "executionData": { }
}
```
For notebooks: no body needed (or pass `{ "executionData": { "parameters": { "key": "value" } } }`)
For pipelines: no body needed
LRO — returns `202` with `x-ms-operation-id`.

## Cancel Job
```
POST /v1/workspaces/{workspaceId}/items/{itemId}/jobs/instances/{jobInstanceId}/cancel
```

## List Job Instances
```
GET /v1/workspaces/{workspaceId}/items/{itemId}/jobs/instances
GET /v1/workspaces/{workspaceId}/items/{itemId}/jobs/instances?continuationToken={token}
```
Response: `{ "value": [{ "id", "status", "startTimeUtc", "endTimeUtc", "failureReason" }] }`
Statuses: `NotStarted`, `InProgress`, `Completed`, `Failed`, `Cancelled`, `Deduped`

## Get Job Instance
```
GET /v1/workspaces/{workspaceId}/items/{itemId}/jobs/instances/{jobInstanceId}
```

## Create Schedule
```
POST /v1/workspaces/{workspaceId}/items/{itemId}/jobs/schedules
```
Body:
```json
{
  "type": "Cron",
  "configuration": {
    "startDateTime": "2026-03-10T08:00:00Z",
    "endDateTime": "2026-12-31T23:59:59Z",
    "cronExpression": "0 0 8 * * ?",
    "timeZone": "UTC"
  },
  "enabled": true,
  "owner": { "id": "uuid", "type": "User" }
}
```

## Get Schedule
```
GET /v1/workspaces/{workspaceId}/items/{itemId}/jobs/schedules/{scheduleId}
```

## Update Schedule
```
PATCH /v1/workspaces/{workspaceId}/items/{itemId}/jobs/schedules/{scheduleId}
```
Body: same shape as Create, with only fields to update.

## Delete Schedule
```
DELETE /v1/workspaces/{workspaceId}/items/{itemId}/jobs/schedules/{scheduleId}
```

## List Schedules
```
GET /v1/workspaces/{workspaceId}/items/{itemId}/jobs/schedules
```

## Permissions
- Scope: `Item.Execute.All` or `{ItemType}.Execute.All`
