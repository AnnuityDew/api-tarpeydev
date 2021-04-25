# import third party packages
import sqlalchemy
from sqlalchemy import create_engine
from motor.motor_asyncio import AsyncIOMotorClient

# import custom local stuff
from instance.config import MONGO_CONNECT
from src.db.sqlite import engine_object
from src.db.atlas import atlas_object


async def motor_startup():
    """Startup a motor client at app startup.

    https://github.com/markqiu/fastapi-mongodb-realworld-example-app/
    blob/master/app/db/mongodb_utils.py#L10
    """
    atlas_object.client = AsyncIOMotorClient(
        MONGO_CONNECT,
        # maxPoolSize=15,
        maxIdleTimeMS=1000*60*3,
    )


async def motor_shutdown():
    """Shutdown the motor client at app shutdown."""
    atlas_object.client.close()


async def sqlite_startup():
    """Startup a SQLAlchemy engine at app startup."""
    engine_object.engine = create_engine("sqlite+pysqlite:///db.sqlite", echo=True, future=True)


async def sqlite_shutdown():
    return