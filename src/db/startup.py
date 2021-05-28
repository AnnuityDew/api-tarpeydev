import os
from pathlib import Path

# import third party packages
from sqlalchemy import create_engine

# import custom local stuff
from src.db.alchemy import engine_object


async def alchemy_startup():
    """Startup a SQLAlchemy engine at app startup."""
    if os.getenv("ENVIRONMENT") == "no":
        pass
        # storage_client = storage.Client()
        # bucket = storage_client.bucket("tarpeydev-sqlite")
        # blob = bucket.blob("db.sqlite")
        # db_folder_path = Path("src/db")
        # db_file_path = db_folder_path / "db.sqlite"
        # blob.download_to_filename(db_file_path)
        # engine_object.engine = create_engine(
        #     f"sqlite+pysqlite:///{db_file_path}", echo=True, future=True
        # )
    else:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_name = os.getenv("DB_NAME")
        if os.getenv("ENVIRONMENT") == "test":
            # settings for connecting locally through cloud_sql_proxy
            db_host = os.getenv("DEV_DB_HOST")
            db_port = os.getenv("DB_PORT")
            echo_on = True
            connect_string = (
                f"postgresql+psycopg2://{db_user}:{db_password}@"
                + f"{db_host}:{db_port}/{db_name}"
            )
        else:
            # settings for a Cloud Run <-> Cloud SQL connection
            # uses Unix sockets instead of TCP
            db_socket_dir = os.getenv("DB_SOCKET_DIR")
            cloud_sql_instance_name = os.getenv("CLOUD_SQL_INSTANCE_NAME")
            echo_on = False
            connect_string = (
                f"postgresql+psycopg2://{db_user}:{db_password}@/{db_name}"
                + f"?host={db_socket_dir}/{cloud_sql_instance_name}"
            )

        engine_object.engine = create_engine(
            connect_string,
            echo=echo_on,
            future=True,
        )
    
    if os.getenv("INIT") == "yes":
        return engine_object.engine
    elif os.getenv("ALEMBIC") == "yes":
        return connect_string


async def alchemy_shutdown():
    print("App shutdown complete!")
