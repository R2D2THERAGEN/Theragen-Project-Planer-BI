# Power BI Reports API

Base: `https://api.powerbi.com/v1.0/myorg`

## Export to File (LRO)
```
POST /v1.0/myorg/groups/{groupId}/reports/{reportId}/ExportTo
```
Body:
```json
{
  "format": "PDF",
  "powerBIReportConfiguration": {
    "pages": [
      {
        "pageName": "ReportSection1",
        "visualName": "Visual1",
        "bookmark": { "state": "bookmarkState123" }
      }
    ],
    "reportLevelFilters": [
      { "filter": "Sales/Region eq 'North'" }
    ],
    "defaultBookmark": { "name": "MyBookmark" },
    "locale": "en-US"
  }
}
```
Formats: `PDF`, `PPTX`, `PNG`, `DOCX`, `XLSX`, `CSV`, `XML`, `MHTML`, `IMAGE`
Returns `202` with export ID.

## Get Export Status
```
GET /v1.0/myorg/groups/{groupId}/reports/{reportId}/exports/{exportId}
```
Response: `{ "id", "status", "percentComplete", "reportId", "reportName", "resourceLocation", "resourceFileExtension", "expirationTime" }`
Statuses: `NotStarted`, `Running`, `Succeeded`, `Failed`

## Download Export
```
GET /v1.0/myorg/groups/{groupId}/reports/{reportId}/exports/{exportId}/file
```
Returns binary file content.

## Clone Report
```
POST /v1.0/myorg/groups/{groupId}/reports/{reportId}/Clone
```
Body: `{ "name": "Cloned Report", "targetModelId": "uuid", "targetWorkspaceId": "uuid" }`

## Rebind Report
```
POST /v1.0/myorg/groups/{groupId}/reports/{reportId}/Rebind
```
Body: `{ "datasetId": "new-dataset-uuid" }`

## Get Pages
```
GET /v1.0/myorg/groups/{groupId}/reports/{reportId}/pages
```
Response: `{ "value": [{ "name": "ReportSection1", "displayName": "Overview", "order": 0 }] }`
Use `name` values for the export `pages` parameter.

## Export Workflow

1. **Get pages:** `GET .../reports/{id}/pages` to discover page names
2. **Start export:** `POST .../reports/{id}/ExportTo` with desired format and pages
3. **Poll status:** `GET .../reports/{id}/exports/{exportId}` until `Succeeded`
4. **Download:** `GET .../reports/{id}/exports/{exportId}/file`
