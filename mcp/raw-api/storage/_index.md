# OneLake Storage API (ADLS Gen2)

Base: varies per account
Audience: `storage`

OneLake uses Azure Data Lake Storage Gen2 (ADLS Gen2) REST API underneath.
Base URL: `https://onelake.dfs.fabric.microsoft.com`

## Path Format
```
https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files/{path}
https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Tables/{tableName}
```
You can also use workspace/item display names:
```
https://onelake.dfs.fabric.microsoft.com/{workspaceName}/{itemName}.Lakehouse/Files/{path}
```

## List (ls)
```
GET https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files?resource=filesystem&recursive=false
```
Query params:
- `resource=filesystem` — required
- `directory={path}` — subdirectory to list
- `recursive=true|false`
- `maxResults={n}`
- `continuation={token}`

Response header: `x-ms-continuation` for pagination.
Response body: `{ "paths": [{ "name", "isDirectory", "contentLength", "lastModified" }] }`

## Read File
```
GET https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files/{filePath}
```
Returns file content. Set `Range` header for partial reads: `Range: bytes=0-1023`

## Create / Write File
Three steps for new files:

### 1. Create
```
PUT https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files/{filePath}?resource=file
```

### 2. Append
```
PATCH https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files/{filePath}?action=append&position=0
```
Body: raw file content.

### 3. Flush (commit)
```
PATCH https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files/{filePath}?action=flush&position={totalBytes}
```

## Overwrite File (simpler)
```
PUT https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files/{filePath}?resource=file
```
Then single append + flush.

## Delete
```
DELETE https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files/{filePath}
DELETE https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files/{dirPath}?recursive=true
```

## Create Directory
```
PUT https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files/{dirPath}?resource=directory
```

## Get Properties
```
HEAD https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{itemId}/Files/{filePath}
```
Returns metadata in response headers: `Content-Length`, `Last-Modified`, `x-ms-properties`.

## Auth
- Token scope: `https://storage.azure.com/.default`
- Pass as `Authorization: Bearer {token}` header
- Use `x-ms-version: 2021-08-06` header
