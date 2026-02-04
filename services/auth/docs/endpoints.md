# Identity Service API (v1)

## 1) JWKS (публичные ключи для проверки JWT)

### `GET /.well-known/jwks.json`
**Назначение:** выдаёт набор публичных ключей (JWKS), чтобы Gateway и другие сервисы могли валидировать **ACCESS JWT** по `kid` без ручной раздачи ключей.

**Ключевые заметки**
- JWT содержат `iss` (issuer) и `kid` (key id).
- Gateway кэширует JWKS и обновляет при неизвестном `kid` / по TTL.

---

## 2) OTP subsystem (отдельная подсистема)

### `POST /v1/auth/otp/request`
**Назначение:** инициирует отправку OTP на email (или другой канал), с учётом rate limit/cooldown.

**Когда используется**
- регистрация
- логин (password + OTP)
- step-up (L2)
- password reset
- подтверждение нового email

**Ожидаемая семантика**
- создаёт challenge (`otp_id`), задаёт TTL и лимиты на попытки;
- возвращает `otp_id`, TTL и `cooldown_seconds`.

---

### `POST /v1/auth/otp/verify`
**Назначение:** проверяет OTP-код и выдаёт **`otp_token`** (короткоживущий одноразовый токен-доказательство).

**Когда используется**
- перед `login`, `register`, `step-up`, `password reset` и т.п.

**Почему так**
- код OTP не “путешествует” по разным эндпоинтам: валидация централизована;
- `otp_token` можно сделать одноразовым, привязанным к пользователю и `device_id`. **(потом можно привязать к purpose)**

---

## 3) Регистрация и подтверждение email

### `POST /v1/auth/register`
**Назначение:** создаёт пользователя и первую device session, выдаёт `ACCESS/REFRESH`.

**Типовой поток**
1) `otp/request` (purpose=register) → отправка кода  
2) `otp/verify` → получение `otp_token`  
3) `register` → создание аккаунта + выдача токенов

**Особенности**
- пароль хешируется (bcrypt/argon2);

---

### `POST /v1/auth/email/change`
**Назначение:** смена email (критическая операция), требует **L2**.

**Рекомендуемая логика**
- пользователь делает step-up (L2),
- запрашивает OTP на новый email,
- подтверждает `otp_token` и меняет email.

---

## 4) Аутентификация: login / refresh / logout

### `POST /v1/auth/login`
**Назначение:** логин (password + OTP) → выдача `ACCESS/REFRESH` и создание/обновление device session (`sid`).

**Типовой поток**
1) `otp/request` (purpose=login)  
2) `otp/verify` → `otp_token`  
3) `login` (password + otp_token + device meta)

**Заметки**
- здесь же обновляются метаданные сессии (UA/IP/client_version/last_seen);
- базово можно всегда требовать OTP (как в задумке), “remember device” — позже.

---

### `POST /v1/auth/refresh`
**Назначение:** обновляет токены по REFRESH с **rotation** и **reuse detection**.

**Семантика**
- проверяет, что refresh относится к активной `sid` и не отозван;
- инвалидирует старый refresh, выдаёт новый refresh + новый access;
- при повторном использовании старого refresh → `REFRESH_REUSE_DETECTED` и немедленный revoke `sid`.

---

### `POST /v1/auth/logout`
**Назначение:** выход с текущего устройства — отзыв текущей `sid`.

**Заметки**
- refresh становится непригодным сразу;
- L1-доступ (access) сохраняется только до истечения TTL.

---

## 5) Step-up (L2)

### `POST /v1/auth/step-up`
**Назначение:** повышает уровень доверия до L2 на короткое окно (`recent_auth_until`), используя OTP.

**Типовой поток**
1) `otp/request` (purpose=step_up)  
2) `otp/verify` → `otp_token`  
3) `step-up` → `recent_auth_until = now + window`

---

## 6) Управление device sessions (устройства)

### `GET /v1/auth/sessions`
**Назначение:** возвращает список device sessions пользователя (для “Безопасность / Устройства”).

**Типичные поля**
- `sid`, `device_id`, статус (`active/revoked`), `created_at`, `last_seen_at`,
- метаданные: `platform`, `device_name`, `client_version`, `ip_last`, `ua_last`,
- `recent_auth_until`.

---

### `GET /v1/auth/sessions/current`
**Назначение:** возвращает информацию по **текущей** session (удобно для UI и дебага).

---

### `POST /v1/auth/sessions/{sid}/revoke`
**Назначение:** отзыв конкретной session (например “выйти с другого устройства”).

**Заметка**
- доступно по L1, но сервер проверяет, что `sid` принадлежит текущему `sub`.

---

### `POST /v1/auth/sessions/revoke-all`
**Назначение:** отзыв **всех** сессий пользователя (критическое действие) — требует **L2**.

**Ожидаемая проверка**
- перед выполнением Edge вызывает internal `l2/check` по `sid`.

---

## 7) Пароль и восстановление доступа

### `POST /v1/auth/password/change`
**Назначение:** смена пароля (критическая) — требует **L2**.

**Рекомендуемая логика**
- проверка текущего пароля;
- установка нового пароля;
- revoke всех сессий кроме текущей (или всех — по политике).

---

### `POST /v1/auth/password/reset/request`
**Назначение:** инициирует восстановление доступа (unauth): отправляет OTP с purpose=`password_reset`.

**Типовой поток**
1) `password/reset/request` → отправка OTP  
2) `otp/verify` → `otp_token`  
3) `password/reset/confirm` → смена пароля

---

### `POST /v1/auth/password/reset/confirm`
**Назначение:** подтверждает reset по `otp_token` и устанавливает новый пароль (unauth).

**Рекомендуемая опция**
- `revoke_all_sessions: true` по умолчанию (после reset обычно нужно “выкинуть” все старые сессии).

---

## 8) Аккаунт (критические операции)

### `POST /v1/auth/account/delete`
**Назначение:** удаление аккаунта (критическое) — требует **L2**.

**Заметки**
- требуются ввод пароля (защита от случайного удаления);
- после удаления: revoke всех session + инвалидирование refresh.

---

## 9) Internal endpoints (только для Gateway/сервисов)

> Эти эндпоинты должны быть **недоступны публично**: ограничение по сети, mTLS, internal auth token или allowlist.

### `POST /v1/internal/l2/check`
**Назначение:** stateful L2-проверка по `sid` перед критическими деяйствиями на Edge.

**Возвращает**
- активна ли session,
- активен ли `recent_auth_until`,
- и причину отказа (`STEP_UP_REQUIRED`, `SESSION_REVOKED`).

---

### `POST /v1/internal/sessions/{sid}/revoke`
**Назначение:** отзыв session из внутренних security-событий (например, при `REFRESH_REUSE_DETECTED`, подозрительной активности и т.д.).

---

## Приложение: рекомендуемые коды ошибок (семантика)
- `INVALID_CREDENTIALS`
- `INVALID_TOKEN`
- `TOKEN_EXPIRED`
- `SESSION_REVOKED`
- `STEP_UP_REQUIRED`
- `REFRESH_REUSE_DETECTED`
- `OTP_INVALID`
- `OTP_EXPIRED`
- `OTP_COOLDOWN`
- `RATE_LIMITED`