# Domains API (Core)

Base: `https://api.fabric.microsoft.com/v1`

## Get Domain
```
GET /v1/domains/{domainId}
```

## List Domains
```
GET /v1/domains
```
Response: `{ "value": [{ "id", "displayName", "description", "parentDomainId" }] }`

Note: For full domain management (create, update, delete, assign workspaces), use the Admin APIs — see `admin.md`.
