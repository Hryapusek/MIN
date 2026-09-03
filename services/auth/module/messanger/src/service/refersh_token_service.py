import secrets
import datetime
import uuid
import hashlib

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from messanger.src.core.settings import get_settings

from messanger.src.db.refresh_token import RefreshToken
from messanger.src.db.device_session import DeviceSession


ENTROPY_BYTES = 32  # Length of generated token

class DeviceSessionExpiredError(Exception):
    pass

class DeviceSessionRevokedError(Exception):
    pass

class RefreshTokenError(Exception):
    pass

class RefreshTokenReusageDetectedError(Exception):
    pass

class IssuedRefreshToken:
    def __init__(self, token: str, expires_at: datetime.datetime):
        self.token = token
        self.expires_at = expires_at

def _generate_refresh_token() -> str:
    return secrets.token_urlsafe(nbytes=ENTROPY_BYTES)

def _calculate_refresh_token_expire_at():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=get_settings().REFRESH_TOKEN_EXPIRE_PERIOD_DAYS)    

def _create_refresh_token(device_session: DeviceSession) -> tuple[RefreshToken, IssuedRefreshToken]:
    raw_roken = _generate_refresh_token()
    expires_at = _calculate_refresh_token_expire_at()
    new_refresh_token = RefreshToken(
        token_hash=hashlib.sha256(
            raw_roken.encode("UTF-8")
        ).digest(),
        expires_at=expires_at,
    )
    new_refresh_token.device_session = device_session
    
    return (new_refresh_token, IssuedRefreshToken(token=raw_roken, expires_at=expires_at))


class RefreshTokenService:

    async def issue(
        session: AsyncSession, device_session: DeviceSession
    ) -> IssuedRefreshToken:
        if device_session.revoked_at is not None:
            raise DeviceSessionExpiredError()
        
        if device_session.idle_expires_at <= datetime.datetime.now():
            raise DeviceSessionRevokedError()
        
        new_refresh_token, issued_token = _create_refresh_token(device_session=device_session)

        session.add(new_refresh_token)
        return issued_token
    
    async def rotate(
        refresh_token_str: str, session: AsyncSession
    ) -> IssuedRefreshToken:
        if refresh_token.expires_at <= datetime.datetime.now():
            raise RefreshTokenError()
        
        if refresh_token.device_session.revoked_at is not None:
            raise DeviceSessionExpiredError()
                    
        if refresh_token.device_session.idle_expires_at <= datetime.datetime.now():
            raise DeviceSessionRevokedError()
        
        if refresh_token.consumed_at is not None:
            raise RefreshTokenReusageDetectedError()
        
        result = await session.execute(select(RefreshToken).where(token_hash=refresh_token_str).with_for_update())
        
        refresh_token = result.one()
        
        new_refresh_token, issued_token = _create_refresh_token(device_session=refresh_token.device_session)
        
        refresh_token.consumed_at = datetime.datetime.now(datetime.timezone.utc)
        
        refresh_token.replaced_by = new_refresh_token
        
        new_refresh_token.previous_token = refresh_token
        
        session.add(new_refresh_token)
        
        return issued_token
