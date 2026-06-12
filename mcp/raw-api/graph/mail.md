# Graph — Mail API

Base: `https://graph.microsoft.com/v1.0`

## Send Mail
```
POST /v1.0/me/sendMail
```
Body:
```json
{
  "message": {
    "subject": "Project Update",
    "body": {
      "contentType": "HTML",
      "content": "<h1>Update</h1><p>The pipeline completed.</p>"
    },
    "toRecipients": [
      { "emailAddress": { "address": "alice@company.com", "name": "Alice" } },
      { "emailAddress": { "address": "bob@company.com" } }
    ],
    "ccRecipients": [
      { "emailAddress": { "address": "manager@company.com" } }
    ],
    "bccRecipients": [],
    "importance": "High",
    "attachments": [
      {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": "report.pdf",
        "contentType": "application/pdf",
        "contentBytes": "base64-encoded-content"
      }
    ]
  },
  "saveToSentItems": true
}
```
Content types: `Text`, `HTML`
Importance: `Low`, `Normal`, `High`

## List Messages
```
GET /v1.0/me/messages
GET /v1.0/me/messages?$top=10&$orderby=receivedDateTime desc&$select=subject,from,receivedDateTime,isRead
GET /v1.0/me/messages?$filter=isRead eq false
```

## Get Message
```
GET /v1.0/me/messages/{messageId}
```

## Reply to Message
```
POST /v1.0/me/messages/{messageId}/reply
```
Body: `{ "comment": "Thanks for the update!" }`

## Forward Message
```
POST /v1.0/me/messages/{messageId}/forward
```
Body: `{ "comment": "FYI", "toRecipients": [{ "emailAddress": { "address": "dean@company.com" } }] }`

## Delete Message
```
DELETE /v1.0/me/messages/{messageId}
```

## Search Mail
```
GET /v1.0/me/messages?$search="subject:pipeline"
```
Requires header: `ConsistencyLevel: eventual`
