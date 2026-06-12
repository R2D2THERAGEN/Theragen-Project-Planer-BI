# Deployment Pipelines API

Base: `https://api.fabric.microsoft.com/v1`

## List Deployment Pipelines
```
GET /v1/deploymentPipelines
GET /v1/deploymentPipelines?continuationToken={token}
```
Response: `{ "value": [{ "id", "displayName", "description" }], "continuationToken" }`

## Create Deployment Pipeline
```
POST /v1/deploymentPipelines
```
Body:
```json
{
  "displayName": "My CI/CD Pipeline",
  "description": "Dev → Test → Prod"
}
```

## Get Deployment Pipeline
```
GET /v1/deploymentPipelines/{pipelineId}
```

## Update Deployment Pipeline
```
PATCH /v1/deploymentPipelines/{pipelineId}
```
Body: `{ "displayName": "New Name", "description": "Updated" }`

## Delete Deployment Pipeline
```
DELETE /v1/deploymentPipelines/{pipelineId}
```

## List Pipeline Stages
```
GET /v1/deploymentPipelines/{pipelineId}/stages
```
Response: `{ "value": [{ "id", "displayName", "description", "order", "isPublic", "workspaceId", "workspaceName" }] }`
`order`: 0 = Development, 1 = Test, 2 = Production

## List Stage Items
```
GET /v1/deploymentPipelines/{pipelineId}/stages/{stageId}/items
```
Response: `{ "value": [{ "itemId", "itemDisplayName", "itemType", "lastDeploymentTime", "sourceItemObjectId", "targetItemObjectId" }] }`

## Assign Workspace to Stage
```
POST /v1/deploymentPipelines/{pipelineId}/stages/{stageId}/assignWorkspace
```
Body: `{ "workspaceId": "uuid" }`

## Unassign Workspace from Stage
```
POST /v1/deploymentPipelines/{pipelineId}/stages/{stageId}/unassignWorkspace
```
No body.

## Deploy Stage Content (LRO)
```
POST /v1/deploymentPipelines/{pipelineId}/deploy
```
Body:
```json
{
  "sourceStageId": "dev-stage-uuid",
  "targetStageId": "test-stage-uuid",
  "items": [
    { "sourceItemId": "uuid", "itemType": "SemanticModel" },
    { "sourceItemId": "uuid", "itemType": "Report" }
  ],
  "note": "Deploying v2.1 to test",
  "isBackwardDeployment": false,
  "newWorkspace": {
    "capacityId": "uuid"
  }
}
```
Key fields:
- `items` — specific items to deploy. Omit to deploy all.
- `isBackwardDeployment` — `true` for Prod → Test (rollback)
- `newWorkspace` — auto-create target workspace if stage has no workspace

Response: `202 Accepted` with LRO headers.

## List Deployment Operations
```
GET /v1/deploymentPipelines/{pipelineId}/operations
```
Response: `{ "value": [{ "id", "type", "status", "sourceStageId", "targetStageId", "createdDateTime", "lastUpdatedDateTime", "executionPlan" }] }`

## Role Assignments

### List
```
GET /v1/deploymentPipelines/{pipelineId}/roleAssignments
```

### Add
```
POST /v1/deploymentPipelines/{pipelineId}/roleAssignments
```
Body: `{ "principal": { "id": "uuid", "type": "User" }, "role": "Admin" }`
Roles: `Admin`

### Delete
```
DELETE /v1/deploymentPipelines/{pipelineId}/roleAssignments/{roleAssignmentId}
```

## Typical CI/CD Workflow

1. Create pipeline: `POST /v1/deploymentPipelines`
2. Assign workspaces to stages: Dev → stage 0, Test → stage 1, Prod → stage 2
3. Make changes in Dev workspace
4. Deploy Dev → Test: `POST /v1/deploymentPipelines/{id}/deploy`
5. Validate in Test
6. Deploy Test → Prod
7. Monitor with List Operations

## Permissions
- Pipeline CRUD: requires pipeline Admin role
- Deploy: requires Contributor+ on both source and target workspaces
- Scope: `Pipeline.ReadWrite.All` or `Pipeline.Read.All` (read-only)
