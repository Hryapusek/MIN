## 1️⃣ Users
```sql
CREATE TABLE users (
    id                  UUID PRIMARY KEY,
    email               TEXT NOT NULL UNIQUE,
    -- email_verified      BOOLEAN NOT NULL DEFAULT FALSE,
    password_hash       TEXT NOT NULL,
    -- role                TEXT NOT NULL DEFAULT 'user',
    -- is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    -- token_version       INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

2️⃣ Device Sessions
```sql
CREATE TABLE device_sessions (
    sid                 UUID PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id           TEXT NOT NULL,

    status              TEXT NOT NULL CHECK (status IN ('active', 'revoked')),

    refresh_token_hash  TEXT NOT NULL,
    -- recent_auth_until   TIMESTAMPTZ,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    ip_last             INET,
    ua_last             TEXT,
    client_version      TEXT
);

CREATE INDEX idx_sessions_user_id ON device_sessions(user_id);
CREATE INDEX idx_sessions_refresh_hash ON device_sessions(refresh_token_hash);
```

**ip_last** – type INET
Stores the last IP address seen for this device session.
Helps detect suspicious logins (e.g., a session suddenly coming from a different country).
Useful for security dashboards (“last login from IP x.x.x.x”).
Can also be used for rate-limiting, geolocation features, or blocking malicious IPs.

Notes:
INET is a PostgreSQL type for IPv4 or IPv6 → better than TEXT for indexing and querying.
Only stores last seen IP, not the entire history (for storage efficiency).

**ua_last** – type TEXT
Purpose:
Stores the User-Agent string from the client (browser, OS, app version).
Helps identify device type, OS, app version, or unusual sessions.
Useful for security alerts (unknown device) and debugging issues.

Notes:
Could be TEXT because User-Agent strings vary in length.

Optional: you could parse and store platform or device_name separately for easier reporting.

**client_version** – type TEXT

Purpose:
Specifically stores the version of your app (mobile app, desktop, or web client).
Helps with rolling out features gradually, tracking bugs, or deprecating old clients.
Can be combined with ua_last to detect outdated or insecure clients.

Notes:
Could use semantic versioning strings (1.3.5) or numeric representation (10305).
Optional, but helpful for analytics and security.

3️⃣ OTP Challenges

This is critical and was missing before.

```sql
CREATE TABLE otp_challenges (
    id                  UUID PRIMARY KEY,       -- otp_id
    user_id             UUID,                   -- nullable for unauth flows
    email               TEXT NOT NULL,

    purpose             TEXT NOT NULL CHECK (
        purpose IN (
            'register',
            'login',
            'step_up',
            'password_reset',
            'email_change'
        )
    ),

    code_hash           TEXT NOT NULL,
    expires_at          TIMESTAMPTZ NOT NULL,
    attempts_left       INTEGER NOT NULL DEFAULT 5,
    cooldown_until      TIMESTAMPTZ,

    consumed            BOOLEAN NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

```sql
CREATE TABLE otp_tokens (
    id                  UUID PRIMARY KEY,
    user_id             UUID,
    device_id           TEXT,

    purpose             TEXT NOT NULL,
    expires_at          TIMESTAMPTZ NOT NULL,
    consumed            BOOLEAN NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

```
device_id = UUIDv4()
store_in_secure_storage(device_id)
```

```sql
CREATE TABLE email_change_requests (
    id                  UUID PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    new_email           TEXT NOT NULL,
    otp_token_id        UUID NOT NULL REFERENCES otp_tokens(id),
    expires_at          TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

```sql
CREATE TABLE signing_keys (
    kid                 TEXT PRIMARY KEY,
    algorithm           TEXT NOT NULL,         -- RS256, EdDSA etc
    public_key_pem      TEXT NOT NULL,
    private_key_pem     TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('active','retired')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

# NOT VERIFIED
Why store?

Because:
You need rotation
You need multiple active keys
JWKS endpoint serves public keys where status='active' OR recently retired

7️⃣ Security Events (Very Recommended)
```sql
CREATE TABLE security_events (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID,
    sid             UUID,
    type            TEXT NOT NULL,
    ip              INET,
    user_agent      TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Examples:
LOGIN_SUCCESS
LOGIN_FAILED
REFRESH_REUSE_DETECTED
SESSION_REVOKED
PASSWORD_CHANGED
ACCOUNT_DELETED

This is critical for production.

8️⃣ Optional: Login Attempts / Rate Limit Tracking

If not using Redis:

```sql
CREATE TABLE login_attempts (
    id          BIGSERIAL PRIMARY KEY,
    email       TEXT,
    ip          INET,
    success     BOOLEAN,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

But realistically:

Rate limiting belongs in Redis or API Gateway.