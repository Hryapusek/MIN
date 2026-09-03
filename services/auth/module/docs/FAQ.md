# 27 July
## What is the difference between Engine, Connection, and Session?

Engine is a factory for the connections. It maintains a internal connection pool. Also it abstracts us from concrete database type. We dont need to create several instances of this.

```py
from sqlalchemy import create_engine

# Creates the engine manager (does not open a connection yet)
engine = create_engine("postgresql+psycopg2://user:pass@localhost/mydatabase")
```

Connection is a low level interaction with database. It desiged to be used and then closed quickly. Its a physical connection with database.

```py
from sqlalchemy import text

# Checks out a physical connection from the engine's pool
with engine.connect() as connection:
    result = connection.execute(text("SELECT name FROM users WHERE id = :id"), {"id": 1})
    for row in result:
        print(row.name)
# Connection automatically closes and returns to the pool here

```

A Session represents an ORM conversation and transactional unit of work with the database. Unit of work pattern is here. Session track all the changes of objects and then persists them in database when we call `commit()`. Sessions are NOT thread-safe

```py
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)

# Creates a new ORM transactional scope
with SessionLocal() as session:
    # 1. Query an object
    user = session.query(User).filter_by(id=1).first()
    
    # 2. Modify the Python object (tracked automatically)
    user.email = "newemail@example.com" 
    
    # 3. Commit the changes (Session borrows a connection under the hood to execute SQL)
    session.commit() 
```

## Why does Alembic need target_metadata?
Alembic needs target_metadata for autogeneration. It compares the ORM table definitions in Base.metadata against the currently inspected database schema and generates candidate migration operations.

`revision --autogenerate`

## Why should DATABASE_URL come from settings instead of alembic.ini?
DATABASE_URL should come from the application settings so Alembic and the application share one environment-specific configuration source, and credentials do not have to be committed in alembic.ini.

## What does expire_on_commit=False change?

```py
user = session.get(User, user_id)

print(user.email)  # already loaded

session.commit()

# Now in sync code if we set expire_on_commit=True and then access the field like this:
print(user.email)
# We might get an unexpected instructions path. SQLAlchemy will refresh this field according to database implicitly which could BLOCK the main thread. Its simply not possible with async code. In async code we should put await for the operation that potentialy can block our code. But when we access the properties - there is just no way we could insert await somewhere between dot and property name

print(user.await email) # Normal async ORM attribute access cannot transparently perform awaited database I/O. The object must be refreshed explicitly, loaded eagerly, or accessed through SQLAlchemy’s explicit awaitable mechanisms.
```

expire_on_commit=True
    post-commit access may reload current database values

expire_on_commit=False
    post-commit access keeps current in-memory values,
    which may become stale

## Why use migrations instead of Base.metadata.create_all()?

So that we would track unwanted changes or just to make sure that everything goes in the right way. Also create_all does not use alembic and migrations at all. Migrations are useful as hell actually. Its like a git for the code

## What is the difference between an Alembic revision and the current database state?
Alembic revision is like a commit. Current database state is a result of a row of revisions you FEEL ME. Also current database state might differ from revisions if someone for example inserts a trigger in it, but it could be horrible since we should put all the database setup in alembic

## What is the difference between online and offline migrations?
Online migrations run with a database connection and apply operations directly. Offline migrations run without connecting and render SQL for a specified revision range. The generated SQL can be reviewed and applied separately, but migrations that depend on database inspection or runtime data may require special handling.

# 5 August
## Why store a token hash instead of the raw refresh token?
Again its a security reason, we dont want full compromise if our database gets stolen

## Why use SHA-256 for a random token but Argon2 for a password?
Passwords have relatively low, human-generated entropy, so Argon2 intentionally makes every guess expensive. Refresh tokens are generated randomly with very high entropy, making guessing infeasible; therefore fast SHA-256 hashing is suitable and enables efficient database lookup.

## Why is the relationship one device session to many refresh-token rows?
Because we should store consumed refresh tokens for different reasons. We should be able to detect reuse of old tokens.

## What is family_id for?
This is needed for fast reaction in case of token reuse

## What does remote_side mean in a self-referential relationship?
When we specify remote_side on the field - we mean that this field is a parent.

## Why distinguish consumed_at from revoked_at?
It feels more naturally. Consumed and revoked are two different reasons. In case of revokation - family ends

## Why should replaced_by_id be unique?
Because its incorrect invariant if we have several same raplaced_by_id rows values. Chains should not intersect each other

# 3 September
## What is the difference between flush() and commit()?
flush() synchronizes the current ORM state with the database inside the current transaction. SQL is executed and constraints can already fail, but the transaction remains open and can still be rolled back. commit() first flushes pending changes if necessary and then attempts to commit the transaction permanently.

## Why should a lower-level service often call flush() rather than commit()?
Because its a task of a higher function to decide what belongs to the current commit and what does not

## What happens to ORM changes after rollback()?
Rollback reverses the database transaction. Existing persistent ORM objects are expired so they can be reloaded from the database. Objects that were newly inserted during the rolled-back transaction return to a non-persistent/transient state; the Python objects themselves still exist if something references them.

## Why do we hash the provided refresh token before querying the database?
Because we store the tokens as hashes. Therefore we should first prepare the data we are querying with

## Why should refresh-token rotation happen in one transaction?
Transaction is especially important here because we definitely dont want to break invariants of database or leave hanging objects in here or just leave it in any middle state

## What race exists when two requests rotate the same token simultaneously?
Rotating the token effectively is inserting the new token and link it to the previous one. The race is at the point of insertion and issuing. We should check the replaced_by_id and make sure we locked the row before inserting. We can lock the row using with_for_update. Lock is released when the session is commited. But this lock does not mean that other transaction can not read the old value.

## What does SELECT ... FOR UPDATE actually lock, and when is that lock released?
Accidentially answered in the previous block

## Why shouldn't the raw refresh token ever be recoverable from PostgreSQL?
A refresh token is a bearer credential: possession is enough to use it. The server never needs to recover the original value after issuance, only verify a presented value. Therefore storing the raw token would unnecessarily turn a database leak into immediate account/session compromise
