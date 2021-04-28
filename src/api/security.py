import os
from typing import Optional
from fastapi import Depends, APIRouter, HTTPException, Request
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
import httpx
from okta_jwt.jwt import validate_token as validate_locally
from starlette.status import HTTP_401_UNAUTHORIZED


OKTA_AUDIENCE = os.getenv("OKTA_AUDIENCE")
OKTA_CLIENT_ID = os.getenv("OKTA_CLIENT_ID")
OKTA_ISSUER = os.getenv("OKTA_ISSUER")


security_api = APIRouter(
    prefix="/security",
    tags=["security"],
)


# https://github.com/tiangolo/fastapi/issues/774
class Oauth2ClientCredentials(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: str = None,
        scopes: dict = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(clientCredentials={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param


oauth2_scheme = Oauth2ClientCredentials(tokenUrl='security/token')


# Call the Okta API to get an access token
def retrieve_token(authorization, issuer, scope="all_data"):
    headers = {
        "accept": "application/json",
        "authorization": authorization,
        "cache-control": "no-cache",
        "content-type": "application/x-www-form-urlencoded",
    }
    body = {
        "grant_type": "client_credentials",
        "scope": scope,
    }
    url = issuer + "/v1/token"

    response = httpx.post(url, headers=headers, data=body)

    if response.status_code == httpx.codes.OK:
        return response.json()
    else:
        raise HTTPException(status_code=400, detail=response.text)


# Get auth token endpoint
@security_api.post("/token")
def login(request: Request):
    """Behind the scenes, FastAPI is base64-encoding client ID and client secret
    for this authorization header that's going to Okta!

    https://developer.okta.com/docs/guides/implement-client-creds/use-flow/

    """
    return retrieve_token(
        request.headers["authorization"],
        OKTA_ISSUER,
        "all_data",
    )


def validate_jwt(token: str = Depends(oauth2_scheme)):
    try:
        res = validate_locally(
            token,
            OKTA_ISSUER,
            OKTA_AUDIENCE,
            OKTA_CLIENT_ID,
        )
        return bool(res)
    except Exception:
        raise HTTPException(status_code=403, detail="Validation failed!")
