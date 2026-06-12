# Microsoft Graph API — Category Index

Base: `https://graph.microsoft.com/v1.0`
Audience: `graph`

Pick the category below, then read its .md file for full specs.

| Category | File | Key Operations |
|----------|------|----------------|
| Users | `graph/users.md` | Get user, Search users, Get manager/reports, List groups |
| Mail | `graph/mail.md` | Send mail (CC/BCC/attachments), List messages, Get message |
| Teams | `graph/teams.md` | List teams/channels, Post message, Read messages, @mentions |
| Drives (OneDrive/SharePoint) | `graph/drives.md` | List files, Download, Upload, Search, Share |

## Common Patterns

```
/v1.0/me                          ← current user
/v1.0/users/{userId-or-email}     ← specific user
/v1.0/me/messages                 ← current user's mail
/v1.0/me/joinedTeams              ← teams the user is in
```

Query parameters (OData):
- `$select=id,displayName,mail` — pick fields
- `$filter=displayName eq 'Jane'` — filter results
- `$top=10` — limit results
- `$expand=manager` — include related entities
- `$orderby=createdDateTime desc` — sort
- `$search="keyword"` — full-text search (some endpoints)
