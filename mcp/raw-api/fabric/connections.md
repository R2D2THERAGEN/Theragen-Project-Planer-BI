# Connections API

Base: `https://api.fabric.microsoft.com/v1`

## List Connections
```
GET /v1/connections
GET /v1/connections?continuationToken={token}
```

## Create Connection
```
POST /v1/connections
```
Body:
```json
{
  "displayName": "My SQL Connection",
  "connectivityType": "ShareableCloud",
  "connectionDetails": {
    "type": "SQL",
    "creationMethod": "SQL",
    "parameters": [
      { "name": "server", "value": "myserver.database.windows.net" },
      { "name": "database", "value": "mydb" }
    ]
  },
  "privacyLevel": "Organizational",
  "credentialDetails": {
    "credentials": {
      "credentialType": "OAuth2"
    },
    "singleSignOnType": "None"
  }
}
```
Connectivity types: `ShareableCloud`, `PersonalCloud`, `OnPremisesGateway`, `OnPremisesGatewayPersonal`, `VirtualNetworkGateway`
Privacy levels: `None`, `Public`, `Organizational`, `Private`
Credential types: `Anonymous`, `Basic`, `Key`, `OAuth2`, `ServicePrincipal`, `Windows`, `SharedAccessSignature`

## Get Connection
```
GET /v1/connections/{connectionId}
```

## Update Connection
```
PATCH /v1/connections/{connectionId}
```
Body: `{ "displayName": "Updated Name", "connectivityType": "...", "connectionDetails": {...}, "privacyLevel": "..." }`

## Delete Connection
```
DELETE /v1/connections/{connectionId}
```

## List Supported Connection Types
```
GET /v1/connections/supportedConnectionTypes
GET /v1/connections/supportedConnectionTypes?gatewayId={gatewayId}
```

## Role Assignments

### List
```
GET /v1/connections/{connectionId}/roleAssignments
```

### Add
```
POST /v1/connections/{connectionId}/roleAssignments
```
Body: `{ "principal": { "id": "uuid", "type": "User" }, "role": "Owner" }`
Roles: `Owner`, `User`, `UserWithReshare`

### Update
```
PATCH /v1/connections/{connectionId}/roleAssignments/{roleAssignmentId}
```
Body: `{ "role": "UserWithReshare" }`

### Delete
```
DELETE /v1/connections/{connectionId}/roleAssignments/{roleAssignmentId}
```

## Permissions
- Scope: `Connection.ReadWrite.All` or `Connection.Read.All`
