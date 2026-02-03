The scheme looks like this now

```d
Client
   │
   ▼
[SSL handshake / decrypt]   ← IO thread
   │
   ▼
[Queue: ready-to-process jobs]
   │
   ▼
[Worker thread: business logic / DB / auth]
   │
   ▼
[IO thread: encrypt + send response]
   │
   ▼
Client
```

- **IO thread responsibilities**
    - Accept TCP connection
    - Complete SSL handshake
    - Read full request
    - Validate headers minimally (method, size)
    - Enqueue “job” to processing queue

- **Worker thread responsibilities**
    - Pop job from queue
    - Run business logic (auth, DB, message handling)
    - Produce response
    - Send response back via IO thread (which encrypts using SSL)

