from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from messanger.src.core.settings import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)

AsyncSessionMaker = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
