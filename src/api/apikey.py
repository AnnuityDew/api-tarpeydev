from hmac import compare_digest

from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

from starlette.status import HTTP_403_FORBIDDEN

from instance.config import API_KEY, API_KEY_NAME


# api_key_query = APIKeyQuery(name=API_KEY_NAME, auto_error=False)
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
# api_key_cookie = APIKeyCookie(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if compare_digest(api_key_header, API_KEY):
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials!"
        )
