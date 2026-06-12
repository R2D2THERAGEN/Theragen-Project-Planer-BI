# Graph — Drives API (OneDrive / SharePoint)

Base: `https://graph.microsoft.com/v1.0`

## List User's Drives
```
GET /v1.0/me/drives
```

## List Root Items
```
GET /v1.0/me/drive/root/children
GET /v1.0/drives/{driveId}/root/children
```

## List Folder Contents
```
GET /v1.0/me/drive/root:/{path}:/children
GET /v1.0/drives/{driveId}/items/{itemId}/children
```

## Get Item Metadata
```
GET /v1.0/me/drive/items/{itemId}
GET /v1.0/me/drive/root:/{path}
```

## Download File
```
GET /v1.0/me/drive/items/{itemId}/content
GET /v1.0/me/drive/root:/{path}:/content
```
Returns `302` redirect to download URL.

## Upload File (small, <4MB)
```
PUT /v1.0/me/drive/root:/{path}:/content
```
Body: raw file bytes. Content-Type: file's MIME type.

## Upload File (large, >4MB)
```
POST /v1.0/me/drive/root:/{path}:/createUploadSession
```
Body: `{ "item": { "name": "largefile.zip" } }`
Response: `{ "uploadUrl": "..." }` — then PUT chunks to uploadUrl.

## Search Files
```
GET /v1.0/me/drive/root/search(q='keyword')
GET /v1.0/drives/{driveId}/root/search(q='report')
```

## Create Folder
```
POST /v1.0/me/drive/root/children
```
Body: `{ "name": "New Folder", "folder": {}, "@microsoft.graph.conflictBehavior": "rename" }`

## Delete Item
```
DELETE /v1.0/me/drive/items/{itemId}
```

## Copy Item
```
POST /v1.0/me/drive/items/{itemId}/copy
```
Body: `{ "parentReference": { "driveId": "uuid", "id": "target-folder-id" }, "name": "copied-file.xlsx" }`
Returns `202` — async operation.

## Create Share Link
```
POST /v1.0/me/drive/items/{itemId}/createLink
```
Body: `{ "type": "view", "scope": "organization" }`
Types: `view`, `edit`, `embed`
Scopes: `anonymous`, `organization`, `users`

## SharePoint Sites
```
GET /v1.0/sites?search=keyword
GET /v1.0/sites/{siteId}/drives
GET /v1.0/sites/{siteId}/lists
```
