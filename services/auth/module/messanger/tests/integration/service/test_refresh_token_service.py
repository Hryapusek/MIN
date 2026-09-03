
import pytest

from messanger.src.db.session import AsyncSessionMaker
from messanger.src.service.refersh_token_service import RefreshTokenService


@pytest.mark.asyncio
@pytest.mark.integration
async def test_refresh_token_service():
  async with AsyncSessionMaker() as session:
    
    pass
