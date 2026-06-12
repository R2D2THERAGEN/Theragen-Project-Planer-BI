# Git Integration API

Base: `https://api.fabric.microsoft.com/v1`
Required: workspace must be on a Fabric capacity.

## Connect to Git
```
POST /v1/workspaces/{workspaceId}/git/connect
```
Permission: workspace Admin role. Scope: `Workspace.ReadWrite.All`

Body (Azure DevOps):
```json
{
  "gitProviderDetails": {
    "gitProviderType": "AzureDevOps",
    "organizationName": "MyOrg",
    "projectName": "MyProject",
    "repositoryName": "MyRepo",
    "branchName": "main",
    "directoryName": "/"
  }
}
```

Body (GitHub):
```json
{
  "gitProviderDetails": {
    "gitProviderType": "GitHub",
    "ownerName": "owner",
    "repositoryName": "repo",
    "branchName": "main",
    "directoryName": "/"
  },
  "myGitCredentials": {
    "source": "ConfiguredConnection",
    "connectionId": "uuid"
  }
}
```
Note: GitHub requires `myGitCredentials`. AzureDevOps defaults to Automatic.

## Disconnect from Git
```
POST /v1/workspaces/{workspaceId}/git/disconnect
```
No body. Permission: workspace Admin.

## Get Connection
```
GET /v1/workspaces/{workspaceId}/git/connection
```
Response: `{ "gitProviderDetails": { ... }, "gitConnectionState": "Connected|NotConnected|ConnectedAndInitialized", "gitSyncDetails": { "head", "lastSyncTime" } }`

## Get Status (LRO)
```
GET /v1/workspaces/{workspaceId}/git/status
```
Scope: `Workspace.GitUpdate.All` or `Workspace.GitCommit.All`

Response (200 or 202):
```json
{
  "remoteCommitHash": "abc123...",
  "workspaceHead": "def456...",
  "changes": [
    {
      "itemMetadata": { "itemType": "Notebook", "displayName": "ETL", "objectId": "uuid" },
      "workspaceChange": "Modified",
      "remoteChange": "None",
      "conflictType": "None"
    }
  ]
}
```
Change types: `Added`, `Modified`, `Deleted`, `None`
Conflict types: `None`, `SameItem`, `Rename`, `Definition`

## Commit to Git (LRO)
```
POST /v1/workspaces/{workspaceId}/git/commitToGit
```
Scope: `Workspace.GitCommit.All`

Body (commit all):
```json
{
  "mode": "All",
  "workspaceHead": "def456...",
  "comment": "My commit message"
}
```

Body (selective commit):
```json
{
  "mode": "Selective",
  "workspaceHead": "def456...",
  "comment": "Update notebook only",
  "items": [
    { "objectId": "uuid", "logicalId": "logical-id" }
  ]
}
```
Modes: `All`, `Selective`
`workspaceHead` — get from Get Status. `items` — get from Get Status changes.
Max comment length: 300 chars.

## Update from Git (LRO)
```
POST /v1/workspaces/{workspaceId}/git/updateFromGit
```
Scope: `Workspace.GitUpdate.All`

Body:
```json
{
  "remoteCommitHash": "abc123...",
  "workspaceHead": "def456...",
  "conflictResolution": {
    "conflictResolutionType": "Workspace",
    "conflictResolutionPolicy": "PreferWorkspace"
  },
  "options": {
    "allowOverrideItems": true
  }
}
```
Resolution types: `Workspace`, `Remote`
Policies: `PreferWorkspace`, `PreferRemote`
Get `remoteCommitHash` and `workspaceHead` from Get Status.

## Initialize Connection (LRO)
```
POST /v1/workspaces/{workspaceId}/git/initializeConnection
```
Body: `{ "initializationStrategy": "PreferWorkspace" }`
Strategies: `PreferWorkspace`, `PreferRemote`
Call after Connect when workspace and remote both have content.

## Get My Git Credentials
```
GET /v1/workspaces/{workspaceId}/git/myGitCredentials
```

## Update My Git Credentials
```
PATCH /v1/workspaces/{workspaceId}/git/myGitCredentials
```
Body: `{ "source": "ConfiguredConnection", "connectionId": "uuid" }`
Sources: `Automatic`, `ConfiguredConnection`, `None`

## Typical Workflow

1. `Connect` workspace to repo
2. `Initialize Connection` (if both sides have content)
3. `Get Status` to see changes
4. `Commit to Git` or `Update from Git` based on status
5. Always pass `workspaceHead` from latest status to avoid conflicts

## Common Errors
- `WorkspaceNotConnectedToGit` — Connect first
- `WorkspaceHasNoCapacityAssigned` — Workspace needs Fabric capacity
- `WorkspaceHeadMismatch` — Re-fetch status and retry with current head
- `WorkspacePreviousOperationInProgress` — Wait for prior operation
