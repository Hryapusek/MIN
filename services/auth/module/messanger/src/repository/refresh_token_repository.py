import uuid
from typing import List

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from messanger.src.db.refresh_token import RefreshToken


class RefreshTokenRepository:
  async def list(session: AsyncSession) -> List[RefreshToken]:
    scalars = await session.scalars(select(RefreshToken))
    return scalars.all()

  async def add(session: AsyncSession, refresh_token: RefreshToken) -> RefreshToken:
    return session.add(refresh_token)
  
  async def is_family_exists(family_id: uuid.UUID) -> bool: # bad, race condition
    pass
  
  async def is_token_exists(token_hash: bytes) -> bool: # also bad and race condition
    pass
  
