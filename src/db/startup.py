import os
from pathlib import Path

# import third party packages
from sqlalchemy import create_engine
from google.cloud import storage

# import custom local stuff
from src.db.alchemy import engine_object


async def alchemy_startup():
    """Startup a SQLAlchemy engine at app startup."""
    storage_client = storage.Client()
    bucket = storage_client.bucket("tarpeydev-sqlite")
    blob = bucket.blob("db.sqlite")
    db_folder_path = Path("src/db")
    db_file_path = db_folder_path / "db.sqlite"
    blob.download_to_filename(db_file_path)
    if os.getenv("ENVIRONMENT") == "dev":
        db_host = os.getenv("DEV_DB_HOST")
        echo_on = True
    else:
        db_host = os.getenv("DB_HOST")
        echo_on = False

    if os.getenv("ENVIRONMENT") == "no":
        engine_object.engine = create_engine(
            f"sqlite+pysqlite:///{db_file_path}", echo=True, future=True
        )
    else:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        engine_object.engine = create_engine(
            f"postgresql+psycopg2://{db_user}:{db_password}@"
            + f"{db_host}:{db_port}/{db_name}",
            echo=echo_on,
            future=True,
        )
    
    if os.getenv("INIT") == "yes":
        return engine_object.engine


async def alchemy_shutdown():
    print("shutdown!")
