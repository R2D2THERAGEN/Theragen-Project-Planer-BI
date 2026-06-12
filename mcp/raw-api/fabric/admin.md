# Admin APIs — Tenant Settings

Base: `https://api.fabric.microsoft.com/v1`
Requires: Fabric Admin role

## List Tenant Settings
```
GET /v1/admin/tenantsettings
```
Response: `{ "tenantSettings": [{ "settingName", "title", "enabled", "canSpecifySecurityGroups", "tenantSettingGroup", "properties" }] }`

## Update Tenant Setting
```
PATCH /v1/admin/tenantsettings/{settingName}
```
Body: `{ "enabled": true, "enabledSecurityGroups": [{ "id": "uuid" }] }`

## List Capacity Tenant Settings Overrides
```
GET /v1/admin/capacities/{capacityId}/delegatedTenantSettingOverrides
```

## Permissions
- Scope: `Tenant.Read.All` or `Tenant.ReadWrite.All`
- Must be a Fabric Admin

---

# Admin APIs — Workspaces

## List All Workspaces (Tenant-wide)
```
GET /v1/admin/workspaces
GET /v1/admin/workspaces?name={name}&state={state}&type={type}&continuationToken={token}&capacityId={capacityId}
```
Filters: `name`, `state` (Active/Deleted), `type`, `capacityId`
Unlike Core `GET /v1/workspaces`, this returns ALL workspaces in the tenant.

## Get Workspace
```
GET /v1/admin/workspaces/{workspaceId}
```

## List Workspace Access Details
```
GET /v1/admin/workspaces/{workspaceId}/users
```
Returns all users/groups with access and their roles.

## Restore Deleted Workspace
```
POST /v1/admin/workspaces/{workspaceId}/restore
```
Body: `{ "restoredName": "Restored Workspace", "capacityId": "uuid" }`

---

# Admin APIs — Domains

## CRUD
```
List:    GET    /v1/admin/domains
Create:  POST   /v1/admin/domains
Get:     GET    /v1/admin/domains/{domainId}
Update:  PATCH  /v1/admin/domains/{domainId}
Delete:  DELETE /v1/admin/domains/{domainId}
```

### Create Body
```json
{ "displayName": "Finance Domain", "description": "Finance data mesh domain", "parentDomainId": "uuid (optional)" }
```

## Assign Workspaces to Domain
```
POST /v1/admin/domains/{domainId}/assignWorkspaces
```
Body: `{ "workspacesIds": ["uuid1", "uuid2"] }`

## Unassign Workspaces
```
POST /v1/admin/domains/{domainId}/unassignWorkspaces
```
Body: `{ "workspacesIds": ["uuid1"] }`

## Assign by Capacities
```
POST /v1/admin/domains/{domainId}/assignWorkspacesByCapacities
```
Body: `{ "capacitiesIds": ["uuid1"] }`

## Role Assignments
```
GET    /v1/admin/domains/{domainId}/roleAssignments
POST   /v1/admin/domains/{domainId}/roleAssignments
DELETE /v1/admin/domains/{domainId}/roleAssignments/{roleAssignmentId}
```

---

# Admin APIs — Items

## List Items (Tenant-wide)
```
GET /v1/admin/items
GET /v1/admin/items?type={ItemType}&workspaceId={uuid}&capacityId={uuid}&state={state}
```

## Get Item
```
GET /v1/admin/items/{itemId}
```

## List Item Access Details
```
GET /v1/admin/items/{itemId}/users
```

---

# Admin APIs — Labels (Sensitivity)

## Bulk Set Labels
```
POST /v1/admin/items/bulkSetLabels
```
Body:
```json
{
  "items": [
    { "id": "uuid", "type": "SemanticModel" }
  ],
  "labelId": "sensitivity-label-uuid"
}
```

## Bulk Remove Labels
```
POST /v1/admin/items/bulkRemoveLabels
```
Body: `{ "items": [{ "id": "uuid", "type": "Report" }] }`

---

# Admin APIs — Users

## List User Access Entities
```
GET /v1/admin/users/{userId}/access
```
Returns all Fabric/Power BI items the user can access.
