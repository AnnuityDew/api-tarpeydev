# import native Python packages
import os
from datetime import timedelta
from enum import Enum
from typing import Optional

# import third party packages
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from sqlalchemy import select
from sqlalchemy.future import Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, NoResultFound
from passlib.context import CryptContext
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError

# import custom local stuff
from src.db.alchemy import get_alchemy
from src.db.models import UserIn, UserOut, UserDB, UserORM


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


users_api = APIRouter(
    prefix="/users",
    tags=["users"],
)


# security scheme.
# we're overwriting the __call__ method of LoginManager
# from fastapi_login to check for headers first, and only
# check for cookie if no headers exist. it's the opposite
# order of fastapi_login essentially, so the docs will work
# correctly.
class LoginManagerReversed(LoginManager):
    def _token_from_cookie(self, request: Request) -> Optional[str]:
        """
        Simplifying the FastAPI cookie method here. Rather than raise an unnecessary
        exception, if there is no cookie we simply return None and move on to checking
        """
        token = request.cookies.get(self.cookie_name)

        # if not token and self.auto_error:
        # this is the standard exception as raised
        # by the parent class
        # raise InvalidCredentialsException

        return token if token else None

    async def __call__(self, request: Request):
        """
        Couple extra lines added to the __call__ function to add username
        to the request state (so it can be accessed on every page to say hello).
        """
        token = None
        if self.use_cookie:
            token = self._token_from_cookie(request)

        if token is None and self.use_header:
            token = await super(LoginManager, self).__call__(request)

        if token is not None:
            active_user = await self.get_current_user(token)
            request.state.active_user = active_user.username.value
            return active_user

        # No token is present in the request and no Exception has been raised (auto_error=False)
        raise self.not_authenticated_exception


oauth2_scheme = LoginManagerReversed(
    SECRET_KEY,
    token_url="users/token",
    algorithm=ALGORITHM,
    use_cookie=True,
)
oauth2_scheme.cookie_name = "Authorization"
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


@users_api.post("/", response_model=UserOut)
async def create_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        try:
            session.add(
                UserORM(
                    username=form_data.username,
                    password=await get_password_hash(form_data.password),
                )
            )
            session.commit()
        except IntegrityError:
            raise HTTPException(
                status_code=400, detail=f"{form_data.username} is already registered!"
            )

    return {"username": form_data.username}


@users_api.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    engine: Engine = Depends(get_alchemy),
):
    user = await authenticate_user(
        form_data.username,
        form_data.password,
        engine,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password!",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # sub should be unique across entire application, and it
    # should be a string. user.username could instead have a
    # bot prefix for "bot:x" access to do something.
    access_token = oauth2_scheme.create_access_token(
        data={"sub": user.username},
        expires=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@users_api.get("/me", response_model=UserOut)
async def read_self(current_user: UserOut = Depends(oauth2_scheme)):
    return current_user


@users_api.delete("/me")
async def delete_self(
    engine: Engine = Depends(get_alchemy),
    current_user: UserOut = Depends(oauth2_scheme),
):
    with Session(engine) as session:
        sql = select(UserORM).where(UserORM.username == current_user.username)
        try:
            deletion = session.execute(sql).scalar_one()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")
        session.delete(deletion)
        session.commit()

    return {"deleted_user": deletion.username}


@users_api.patch("/password")
async def change_password(
    updated_password: str,
    current_user: UserOut = Depends(oauth2_scheme),
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        sql = select(UserORM).where(UserORM.username == current_user.username)
        # one returns a Row object, which is a named tuple.
        # using scalar_one to access the object directly instead.
        try:
            result = session.execute(sql).scalar_one()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")

        result.password = await get_password_hash(updated_password)
        session.commit()
        session.refresh(result)

    return "Password updated!"


async def verify_password(plain_password, hashed_password):
    return password_context.verify(plain_password, hashed_password)


async def get_password_hash(password):
    return password_context.hash(password)


async def authenticate_user(username: str, password: str, engine: Engine):
    user = await get_user_and_hash(username, engine)
    if not user:
        return None
    if not await verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_and_hash(username: str, engine: Engine):
    # this is where rubber meets the road between tiangolo's tutorial
    # and the fastapi_login docs. the mongo client is passed through
    # when FastAPI calls it. for fastapi_login's decorator, which only
    # passes in the username value of the decoded token, we go out and
    # get the client separately.
    # we could move the FastAPI code to authenticate_user to keep
    # these two more separate, but it doesn't seem necessary since
    # the password gets chopped off by the UserOut model in the /me
    # endpoint.
    with Session(engine) as session:
        sql = select(UserORM).where(UserORM.username == username)
        try:
            user_dict = session.execute(sql).scalar_one()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")

    # if calling through FastAPI login, just return username
    # otherwise, return hashed password so it can be verified
    if user_dict:
        return UserDB(username=user_dict.username, hashed_password=user_dict.password)


@oauth2_scheme.user_loader
async def get_user(username: str):
    engine = await get_alchemy()
    with Session(engine) as session:
        sql = select(UserORM).where(UserORM.username == username)
        try:
            user_dict = session.execute(sql).scalar_one()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")

    if user_dict:
        return UserOut(username=user_dict.username)
