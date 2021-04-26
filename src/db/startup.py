from pathlib import Path

# import third party packages
from sqlalchemy import create_engine
from google.cloud import storage

# import custom local stuff
from src.db.alchemy import engine_object


async def sqlite_startup():
    """Startup a SQLAlchemy engine at app startup."""
    storage_client = storage.Client()
    bucket = storage_client.bucket('tarpeydev-sqlite')
    blob = bucket.blob('db.sqlite')
    db_folder_path = Path('src/db')
    db_file_path = db_folder_path / 'db.sqlite'
    blob.download_to_filename(db_file_path)
    engine_object.engine = create_engine(f"sqlite+pysqlite:///{db_file_path}", echo=True, future=True)


async def sqlite_shutdown():
    print("shutdown!")
