# The "Why" section
First lets compare several options and point their pros and cons
## **HMAC (Shared Secret) – Threats and Limitations**

### How it works
- Client and server share a symmetric secret.
- Client signs requests; server verifies them.

### Key Threats / Weaknesses

| Threat / Situation               | Why it’s dangerous                                                                                                    |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Client compromise**            | Attacker extracts the secret → can authenticate as user indefinitely. Server cannot distinguish attacker from client. |
| **No expiration / revocation**   | Without server state, there’s no natural way to expire keys or revoke them. Compromise is permanent.                  |
| **Multi-device support**         | One secret shared across devices → compromise of one device compromises all.                                          |
| **Server compromise**            | Exposes client secrets (because server stores same secret).                                                           |
| **Replay attacks (if no nonce)** | Attackers can replay old messages unless you add complex state.                                                       |
**Summary:**  
HMAC is **cryptographically secure**, but **delegates all authentication power to the client**, giving the server very little control. Any compromise is catastrophic and permanent.

### What if we add state
What if we add ability to revoke the keys or control the sessions?

> **Adding server-side state does not remove the fundamental risk of HMAC-based auth**, because the server must still store a secret that is _cryptographically equivalent_ to the client’s secret.

Even if you add:
- key expiration
- revocation lists
- per-device secrets
- nonce storage
- session tracking

…the server still must:
- store the **HMAC key itself** (or a value usable to verify signatures)
- keep it **hot in memory** or retrievable
- use it directly to authenticate requests

#### Consequence

| Scenario           | Result                                         |
| ------------------ | ---------------------------------------------- |
| Client compromised | Attacker extracts key → full impersonation     |
| Server memory dump | Attacker extracts keys → can impersonate users |
| Database leak      | Keys or key-derivatives exposed                |
| Insider access     | Symmetric secrets usable immediately           |

State limits _duration_, **not authority**.

#### Conclusion
> **Server-side state does not eliminate symmetric key risk**
> 
> While it is possible to introduce server-side state to enable expiration or revocation of HMAC keys, this does not address the fundamental weakness of symmetric authentication. The server must still store and actively use a secret that is cryptographically equivalent to the client’s secret. As a result, compromise of server memory, storage, or runtime state enables full impersonation of users. This risk is inherent to symmetric authentication models and cannot be mitigated without transitioning to asymmetric key-based authentication.

> This limitation explains why symmetric authentication is generally reserved for controlled environments such as service-to-service communication, while user authentication systems favor asymmetric or token-based designs.

### Reply attack
**Problem:** User can capture the request and resend it exactly as it is
**Solution:** Using nonce and timestamp

#### Nonce (Number used ONCE)
##### What it is

A **random, unique value** generated per request.

Example:
`nonce = "f93a7c1e0b2d4a88"`

##### How it works
- Client generates a fresh nonce
- Includes it in the signed message
- Server remembers used nonces for a short time
- If the same nonce appears again → reject

##### Example signed message

`user_id=42 nonce=f93a7c1e0b2d4a88 payload=send_message`

##### Why it works
- Even if attacker captures the request:
    - Reusing it will reuse the nonce
    - Server detects duplicate → reject

##### Downsides
- Server must **store used nonces**
- Storage grows with traffic (needs TTL / cleanup)

#### Timestamp

###### What it is
A **time value** included in the signed message.
Example:
`timestamp = 1700000123  // Unix time`

##### How it works
- Client sends current time
- Server checks:
    - Is timestamp within acceptable window? (e.g. ±30s)
- If too old or too far in future → reject

##### Example signed message

`user_id=42 timestamp=1700000123 payload=send_message`

##### Why it works
- Old captured requests become invalid quickly
- Server doesn’t need to store anything long-term

##### Downsides
- Requires **clock synchronization**
- Small time drift must be allowed

#### Conclusion
Nonce provides strict replay protection by detecting reused requests, but requires temporary server storage.
Timestamp bounds replay attacks in time and prevents unbounded nonce storage.  
Combined, nonce and timestamp provide strong replay protection with predictable and limited server state.
## **Token-based authentication (JWT / OAuth-inspired)**

### How it works
- **Use access + refresh tokens**
    - Short-lived access token (minutes to hours) for normal requests
    - Long-lived refresh token (days to months) to get new access tokens
        
- **Bind refresh tokens to device/session**
    - Each device gets its **own refresh token**
    - Optionally tie it to a **device key** (asymmetric key)
    - This allows revocation of individual devices
- **Rotate refresh tokens**
    - Each time a refresh token is used:
        - Server invalidates old token
        - Issues new one
    - If stolen token is replayed → immediately detected → revoke session
        
- **Optional trusted device or key-based login**
    - Trusted devices can have **very long-lived refresh tokens**
    - Key-based authentication ensures that **server can revoke** without needing user to type a password
        
- **Re-auth on sensitive actions**
    - Even long-lived sessions should require password / 2FA for dangerous actions
    - This keeps account compromise contained
### Advantages over HMAC

| Situation / Threat      | Token-based mitigation                                                                              |
| ----------------------- | --------------------------------------------------------------------------------------------------- |
| **Token theft**         | Tokens are short-lived; damage is limited. Server can revoke refresh tokens, invalidating sessions. |
| **Password compromise** | Attacker may obtain access token temporarily, but server can revoke or rotate tokens.               |
| **Multi-device login**  | Each session or device can have separate tokens, isolating compromises.                             |
| **User recovery**       | Users can log in and invalidate old sessions or refresh tokens.                                     |

**Summary:**  
Token-based auth **restores server authority**, allowing damage containment, revocation, and session management — problems HMAC cannot handle naturally.

## **Strong / trusted authentication methods (e.g., asymmetric keys, phone auth)**

### How it works
- Device generates keypair (or uses trusted second factor like phone OTP).
- Server stores **public key or device identifier**.
- Device signs challenges to authenticate.
- Session is bound to key/device; revocation is easy and scoped.

> Asymmetric keys are an alternative to refresh tokens

### Advantages

|Benefit|Explanation|
|---|---|
|**Limited blast radius**|Compromise affects only that device.|
|**Per-device sessions**|User can revoke any device independently.|
|**Longer / persistent sessions**|Trusted devices can maintain longer sessions safely.|
|**Secure session control**|Allows user to view and revoke sessions, as seen in VK.|
|**Passwordless login option**|Enhances UX for trusted devices.|

**Summary:**  
Trusted auth methods allow **fine-grained control over sessions** and **more powerful, long-lived authentication** safely, without compromising overall system security.

# Authentication Levels
**Authentication answers two different questions:**
1. _Who are you?_
2. _How confident am I that it’s really you?_
 
## Level 1: Normal session (default)
**Granted by:**
- Valid access token
- Refresh token rotation active

**Allowed actions:**
- Send messages
- Read chats
- Normal API usage

**Characteristics:**
- Long-lived
- Seamless UX
- No password typing
## Level 2: Trusted device session
**Granted by:**
- Token bound to asymmetric device key
- Or phone-based verification

**Allowed actions:**
- Manage sessions
- View security settings
- Extend session lifetime

**Characteristics:**
- Device-bound
- User-visible session control
- Higher trust, still convenient

## Level 3: Sensitive / critical actions (step-up auth)

**Purpose:**
- Operations that **cause permanent or irreversible changes**
- Operations where **account compromise would be catastrophic**
- Actions that require **extra confirmation that the actual user is in control right now**

**Required for:**
- Changing password
- Adding/removing device keys
- Revoking all sessions
- Changing recovery info

**How to satisfy:**
- Re-enter password **OR**
- Sign challenge with trusted device key **OR**
- Phone / 2FA confirmation

**Important rule:**

> Tokens alone are **never sufficient** for sensitive actions.

## Recovery options
### **Stolen access token**

- **What happens:**  
    Short-lived token is stolen. Attacker can perform API actions until it expires.

- **Recovery:**
    - Usually **nothing special needed**; token will expire naturally.
    - Optional: revoke session if immediate invalidation is required.

- **Notes:**
    - Low-risk scenario due to TTL.
    - Damage is naturally limited.

### **Stolen refresh token**

- **What happens:**  
    Attacker can use it to obtain new access tokens indefinitely until refresh token expires or is revoked.
    
- **Recovery:**
    - Rotate refresh token after each use.
    - User can **log in and revoke the affected session(s)**.
        
- **Notes:**
    - Damage is moderate.
    - If device keys or per-device sessions are in use, the compromise may be **scoped to a single device**.

### **Stolen asymmetric key (device key)**

- **What happens:**  
    Attacker can authenticate as that device.
    
- **Recovery:**
    - User can **revoke the compromised device** via session management.
    - Other devices / sessions remain secure.

- **Notes:**
    - Risk is **scoped to one device**.
    - Step-up (L3) operations still require active confirmation if attacker does not have password/OTP.

### **Stolen password**

- **What happens:**  
    Attacker can log in and create new sessions or perform actions where password alone is sufficient.

- **Recovery:**
    - User can **reset the password** (assuming email or phone access is secure).
    - Server should **invalidate old sessions** after password change.
        
- **Notes:**
    - Damage is global across all sessions not protected by device keys or 2FA.
    - Step-up actions may still block attacker if additional factors are required.

### **Stolen email**

- **What happens:**  
    Attacker can intercept verification codes, password resets, OTPs, or notifications sent via email.

- **Recovery:**
    - Possible only if the user can **regain access to the email account**.
    - If no alternate recovery channel (phone, device key) exists, **some account recovery actions may be impossible**.

- **Notes:**
    - Can be high-risk; full account compromise is possible if email is the sole recovery factor.

### **Stolen phone**

- **What happens:**  
    Attacker can intercept SMS OTPs, phone-based verification codes, or device-based step-up challenges.
    
- **Recovery:**
    - Possible if **alternate recovery channels exist** (email, pre-registered trusted device, backup codes).
    - Otherwise, account recovery may be **partially or fully blocked**.

- **Notes:**
    - High-risk if phone is primary step-up factor.
    - Recovery requires pre-existing backup or trusted device; otherwise, some actions may be irrecoverable.

## How to enforce this technically

### Option A: Token claims

Access token contains:

```json
{
	"sub": "user123",
	"auth_level": "normal",   
	"iat": 1700000000,
	"exp": 1700000900 
}
```

Sensitive endpoints require:

`auth_level >= elevated`

---

### Option B: “Recent authentication” window
- After password / key verification:
    - Mark session as “recently authenticated”
    - Valid for N minutes (e.g. 5–10)
- Sensitive actions require this flag

This is how most web apps do it.
## Where should we store login level?
### Option A - Database only
**How it works**
- Token contains only `user_id`, `session_id`
- Server loads session → computes level

**Pros**
- Always correct
- Easy revocation
- Simple mental model

**Cons**
- DB hit on every request
- Harder to scale stateless APIs

### Option B - Token only
**How it works**
- JWT contains `auth_level = L3`
- Server trusts token claim

**Why this is dangerous**
- Token may outlive reality
- Device may be revoked
- User may downgrade trust
- Sensitive permissions get frozen into token

📌 This is how privilege bugs happen.

### Option C - Hybrid
Token consists of:
```json
{
  "sub": "user_id",
  "sid": "session_id",
  "device_id": "abc123",
  "iat": 1700000000,
  "exp": 1700000900,
  "assurance": 2
}
```

**Rules:**
- Token level is a **hint**
- DB is the **source of truth**
- Effective level = `min(token_level, db_level)`

**Uses:**
- Fast rejection of low-level requests
- Stateless routing decisions
- Rate limiting
- UX hints (client knows when to step up)

#### Note
`assurance` field from the access token should only be used for fast checking if we need to elevate the level


# Registration

```
email → verify → login → register device key → trusted session
```

## Anti DOS actions
### The problems
An attacker can try to:
- Spam the registration endpoint with **fake emails/phones**, creating thousands of pending records.
- Flood verification endpoints with code requests.
- Flood login endpoints (password guessing).
- Flood challenge-response (if you use device keys).

The effects:
- Database grows rapidly → storage issues.
- Verification systems get overloaded (email/SMS costs).
- Legitimate users are delayed or blocked.

### How to prevent
#### Limit per client
- **IP rate limits**: e.g., 5 registration attempts per IP per 10 min.
- **Per device / fingerprint limit**: track attempts per device if feasible.

#### Limit per identifier
- Only allow **N verification codes per email/phone per period**.
- Example: 3 codes per 30 min per email.

#### TTL / auto-cleanup
- Pending user records expire after a reasonable time (e.g., 1–24 hours).
- Periodic cleanup job removes old pending accounts.

## Routine
### **Step 0 — Initial request**

- **Client action:** User provides **email or phone**.
- **Server action:**
    1. Validate format (email/phone).
    2. Check **rate limits / backoff / captcha** (prevent DOS).

- **DB effect:**
    - **Create pending user record** in `users` table (minimal info):

- **Notes:**
    - No password, no keys yet.
    - Pending record **expires automatically** after TTL (e.g., 24h).

### **Step 1 — Send verification code**

- **Server action:**
    - Generate OTP / verification code
    - Store code in **pending_verifications table** with expiry

- **Client action:** Receives code via email/SMS.

### **Step 2 — User submits verification code**

- **Server action:**
    1. Check code validity & TTL
    2. Increment attempt counter
    3. If valid → mark user as **verified**

- **Notes:**
    - If verification fails → reject request
    - If TTL expired → require new verification code

### **Step 3 — Password setup**

- **Client action:** User sets **password**
- **Server action:**
    1. Hash password (e.g., Argon2)
    2. Store hashed password in `users` table

- **Optional:** Generate **device key** if client requests it at this step

### **Step 4 — Create session / refresh token**

- **Server action:**
    1. Create **session row** in `sessions` table
	2. Issue **refresh token** (long-lived)
	3. Issue **access token** (short-lived)

- **Notes:**
    - Access token = L1 / default API actions
    - Refresh token = allows session continuation

### **Step 5 — Optional device key registration**

- **Client action:** User generates **asymmetric key**
- **Server action:**
    1. Store **public key** in `device_keys` table


- **Effect:**
    - Session assurance upgraded (L2 / trusted device)
    - Enables **passwordless login** on this device

### **Step 6 — Step-up / high-value actions**

- **Trigger:** For future operations like:
    - Export data
    - Change email
    - Delete account
- **Server action:** Require **step-up** (OTP, device key challenge)
- **DB effect:** None unless action modifies user/session state

### **Step 7 — Cleanup / maintenance**

- **Pending verifications:** expire after TTL
- **Pending users:** delete if verification not completed
- **Sessions / refresh tokens:** rotate/expire per policy

# Login

| Level  | Meaning                            | Examples                            |
| ------ | ---------------------------------- | ----------------------------------- |
| **L1** | Basic authenticated session        | Password login                      |
| **L2** | Trusted device / possession factor | Device key, phone OTP               |
| **L3** | Step-up / high assurance           | Password + OTP, key + user presence |

## **L1 — Basic authentication**

**How obtained:**
- Password login

**Factors:**
- Knowledge (password)

**Notes:**
- Session starts at L1
- Lowest assurance
- No possession proof

## **L2 — Trusted / possession-based authentication**

**How obtained (any one of these):**
- Device key challenge (asymmetric key)
- OTP via verified phone
- OTP via verified email (weaker, but acceptable)

**Factors:**
- Possession (device / phone / email access)

**Notes:**
- Can be obtained directly (key login)
- Or upgraded from L1
- Enables long-lived sessions

## **L3 — Step-up / high assurance**

**How obtained (requires ≥2 factors, one fresh):**

| Starting level | Required step-up                         |
| -------------- | ---------------------------------------- |
| **L2**         | Key + password                           |
| **L2**         | Key + OTP                                |
| **L1**         | Password + OTP                           |
| **L1**         | Password + OTP + device trust (optional) |

**Factors:**
- Knowledge (password)
- Possession (key / phone / email)
- User intent (fresh interaction)

**Notes:**
- Temporary (minutes)
- Never used for login
- Required for critical actions
