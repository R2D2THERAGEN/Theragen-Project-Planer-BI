# Graph — Teams API

Base: `https://graph.microsoft.com/v1.0`

## List Joined Teams
```
GET /v1.0/me/joinedTeams
```
Response: `{ "value": [{ "id", "displayName", "description" }] }`

## List Channels
```
GET /v1.0/teams/{teamId}/channels
```
Response: `{ "value": [{ "id", "displayName", "description", "membershipType" }] }`

## Post Message to Channel
```
POST /v1.0/teams/{teamId}/channels/{channelId}/messages
```
Body:
```json
{
  "body": {
    "contentType": "html",
    "content": "<h2>Pipeline Complete</h2><p>All tables refreshed successfully.</p>"
  },
  "importance": "high"
}
```

## Post Message with @Mention
```json
{
  "body": {
    "contentType": "html",
    "content": "<at id=\"0\">Jane Doe</at> please review the results."
  },
  "mentions": [
    {
      "id": 0,
      "mentionText": "Jane Doe",
      "mentioned": {
        "user": { "id": "user-uuid", "displayName": "Jane Doe", "userIdentityType": "aadUser" }
      }
    }
  ]
}
```

## Post Message with Adaptive Card
```json
{
  "body": { "contentType": "html", "content": "Card attached" },
  "attachments": [
    {
      "id": "card1",
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": "{\"type\":\"AdaptiveCard\",\"version\":\"1.4\",\"body\":[{\"type\":\"TextBlock\",\"text\":\"Pipeline Status\",\"weight\":\"Bolder\"}]}"
    }
  ]
}
```

## Read Messages from Channel
```
GET /v1.0/teams/{teamId}/channels/{channelId}/messages
GET /v1.0/teams/{teamId}/channels/{channelId}/messages?$top=10
```

## Reply to Message
```
POST /v1.0/teams/{teamId}/channels/{channelId}/messages/{messageId}/replies
```
Body: `{ "body": { "contentType": "text", "content": "Done!" } }`

## Send Chat Message (1:1 or group chat)
```
POST /v1.0/chats/{chatId}/messages
```
Same body format as channel messages.

## List Chats
```
GET /v1.0/me/chats
```
