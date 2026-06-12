# Workspaces API

Base: `https://api.fabric.microsoft.com/v1`

## List Workspaces
```
GET /v1/workspaces
GET /v1/workspaces?roles={roles}&continuationToken={token}
```
Query params:
- `roles` — filter: `Admin`, `Member`, `Contributor`, `Viewer` (comma-separated)
- `continuationToken` — pagination token from previous response
- `preferWorkspaceSpecificEndpoints` — `true` to include per-workspace API URLs

Response: `{ "value": [{ "id", "displayName", "type", "description", "capacityId", "capacityAssignmentProgress", "domainId" }], "continuationToken" }`

## Create Workspace
```
POST /v1/workspaces
```
Body:
```json
{
  "displayName": "My Workspace",
  "description": "optional",
  "capacityId": "uuid (optional)",
  "domainId": "uuid (optional)"
}
```
Response: `201` with workspace object.

## Get Workspace
```
GET /v1/workspaces/{workspaceId}
```
Response: full workspace object.

## Update Workspace
```
PATCH /v1/workspaces/{workspaceId}
```
Body: `{ "displayName": "New Name", "description": "New desc" }` — both optional.

## Delete Workspace
```
DELETE /v1/workspaces/{workspaceId}
```
Response: `200` on success.

## Assign to Capacity
```
POST /v1/workspaces/{workspaceId}/assignToCapacity
```
Body: `{ "capacityId": "uuid" }`

## Unassign from Capacity
```
POST /v1/workspaces/{workspaceId}/unassignFromCapacity
```
No body.

## Assign to Domain
```
POST /v1/workspaces/{workspaceId}/assignToDomain
```
Body: `{ "domainId": "uuid" }`

## Unassign from Domain
```
POST /v1/workspaces/{workspaceId}/unassignFromDomain
```
No body.

## List Workspace Role Assignments
```
GET /v1/workspaces/{workspaceId}/roleAssignments
```
Response: `{ "value": [{ "id", "principal": { "id", "displayName", "type", "servicePrincipalDetails" }, "role" }] }`
Roles: `Admin`, `Member`, `Contributor`, `Viewer`
Principal types: `User`, `Group`, `ServicePrincipal`, `ServicePrincipalProfile`

## Add Workspace Role Assignment
```
POST /v1/workspaces/{workspaceId}/roleAssignments
```
Body:
```json
{
  "principal": { "id": "user-or-group-uuid", "type": "User" },
  "role": "Contributor"
}
```

## Update Workspace Role Assignment
```
PATCH /v1/workspaces/{workspaceId}/roleAssignments/{roleAssignmentId}
```
Body: `{ "role": "Admin" }`

## Delete Workspace Role Assignment
```
DELETE /v1/workspaces/{workspaceId}/roleAssignments/{roleAssignmentId}
```

## Provision Identity
```
POST /v1/workspaces/{workspaceId}/provisionIdentity
```
LRO — provisions a managed identity for the workspace.

## Deprovision Identity
```
POST /v1/workspaces/{workspaceId}/deprovisionIdentity
```

## Permissions Required
- List/Get: `Workspace.Read.All` or `Workspace.ReadWrite.All`
- Create/Update/Delete: `Workspace.ReadWrite.All`
- Role assignments: `Workspace.ReadWrite.All` + Admin role on the workspace
