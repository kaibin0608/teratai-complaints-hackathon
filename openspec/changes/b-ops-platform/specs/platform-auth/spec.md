## ADDED Requirements

### Requirement: Seeded users
On startup the API database SHALL contain these users, created if missing and never duplicated:

| username | full_name | role | approval_limit_myr |
|---|---|---|---|
| `officer1` | Aina Rahman | officer | 2000.00 |
| `officer2` | Daniel Lim | officer | 2000.00 |
| `fraud1` | Farid Hassan | fraud | 5000.00 |
| `manager1` | Mei Ling Tan | manager | none |

Each user's password is `teratai123`, stored only as a bcrypt hash.

#### Scenario: Restart keeps one copy
- **WHEN** the server starts twice on the same database
- **THEN** the `users` table holds exactly the four users

### Requirement: Login
`POST /api/auth/login {username, password}` SHALL return `{token, user}` for correct credentials:
- `user` is `{username, full_name, role, approval_limit_myr}`, where the limit is a money string or null.
- `token` is a JWT (HS256, signed with `JWT_SECRET`) that expires after 12 hours.

Wrong credentials SHALL return 401 without saying which part was wrong.

#### Scenario: Officer logs in
- **WHEN** `officer1` logs in with `teratai123`
- **THEN** the response has a token and `user.role = officer`, `user.approval_limit_myr = "2000.00"`

#### Scenario: Wrong password
- **WHEN** `officer1` logs in with `wrong`
- **THEN** the response is 401 with `detail = "wrong username or password"`

### Requirement: Who am I
`GET /api/auth/me` with `Authorization: Bearer <token>` SHALL return the `user` object. A missing, expired or bad token SHALL return 401.

#### Scenario: Expired token
- **WHEN** a token older than 12 hours is sent
- **THEN** the response is 401

### Requirement: Auth switch
`AUTH_REQUIRED` (env, default false) SHALL control requests to the `/api` read routes that carry no token:
- **false:** the request is served as the manager would see it.
- **true:** the response is 401.

A request that carries a token is always served for that user, whatever the switch says. A bad token is always 401. Every `/api` write action SHALL need a valid token, whatever the switch. The contract routes (`/health`, `/complaints`, `/cases/{id}`, `/cases/{id}/actions`, `/cases/{id}/acknowledge`) SHALL never need a token.

#### Scenario: UI before the login page exists
- **WHEN** `AUTH_REQUIRED` is false and `GET /api/cases` is called with no token
- **THEN** every case is listed, as before

#### Scenario: Locked down
- **WHEN** `AUTH_REQUIRED` is true and `GET /api/metrics` is called with no token
- **THEN** the response is 401, and `GET /cases/{id}` still answers without a token

### Requirement: User list
`GET /api/users` SHALL return every user (without password hashes), for the manager's reassign menu. It is manager-only.

#### Scenario: Officer asks
- **WHEN** `officer1` calls `GET /api/users`
- **THEN** the response is 403
