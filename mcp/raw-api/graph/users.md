# Graph — Users API

Base: `https://graph.microsoft.com/v1.0`

## Get Current User
```
GET /v1.0/me
GET /v1.0/me?$select=id,displayName,mail,jobTitle,department
```

## Get User by ID or Email
```
GET /v1.0/users/{userId}
GET /v1.0/users/user@company.com
GET /v1.0/users/{userId}?$select=id,displayName,mail&$expand=manager
```

## Search Users
```
GET /v1.0/users?$filter=startswith(displayName,'Jane')&$top=10
GET /v1.0/users?$search="displayName:Jane"
```
Note: `$search` requires `ConsistencyLevel: eventual` header.

## Get Manager
```
GET /v1.0/me/manager
GET /v1.0/users/{userId}/manager
```

## Get Direct Reports
```
GET /v1.0/me/directReports
GET /v1.0/users/{userId}/directReports
```

## List User's Groups
```
GET /v1.0/me/memberOf
GET /v1.0/users/{userId}/memberOf
```

## Get User Photo
```
GET /v1.0/me/photo/$value
GET /v1.0/users/{userId}/photo/$value
```
Returns binary image.
