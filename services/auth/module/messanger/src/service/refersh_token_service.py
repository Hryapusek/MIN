import secrets
import datetime
import uuid
import hashlib

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from messanger.src.core.settings import get_settings
from messanger.src.repository.refresh_token_repository import RefreshTokenRepository

from messanger.src.db.refresh_token import RefreshToken
from messanger.src.db.device_session import DeviceSession


ENTROPY_BYTES = 32  # Length of generated token


def _generate_refresh_token() -> str:
    return secrets.token_urlsafe(nbytes=ENTROPY_BYTES)


class IssuedRefreshToken:
    def __init__(self, token: str, expires_at: datetime.datetime):
        self.token = token
        self.expires_at = expires_at


class RefreshTokenService:
    async def issue(
        refresh_token_repository: RefreshTokenRepository, session: AsyncSession, device_session: DeviceSession
    ) -> IssuedRefreshToken:
        raw_roken = _generate_refresh_token()
        new_refresh_token = RefreshToken(
            device_session_id=uuid.uuid4(),
            token_hash=hashlib.sha256(
                raw_roken.encode("UTF-8")
            ).digest(),
            family_id=uuid.uuid4(),
            expires_at=datetime.datetime.now() + datetime.timedelta(days=get_settings().REFRESH_TOKEN_EXPIRE_PERIOD_DAYS),
        )
        pass

    pass
