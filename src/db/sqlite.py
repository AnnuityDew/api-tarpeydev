# import third party packages
from sqlalchemy.future import Engine


class SQLiteEngine():
    engine: Engine = None


engine_object = SQLiteEngine()


async def get_odm():
    return engine_object.engine
