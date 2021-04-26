# import third party packages
from sqlalchemy.future import Engine


class SQLiteEngine():
    engine: Engine = None


engine_object = SQLiteEngine()


async def get_sqlite():
    return engine_object.engine
