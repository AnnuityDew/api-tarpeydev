import asyncio
from pathlib import Path
import os

# import third party packages
from motor.motor_asyncio import AsyncIOMotorClient
import pandas as pd

# import custom local stuff

async def full_backup():
    """Backup all database collections from Mongo."""
    client = AsyncIOMotorClient(
        MONGO_CONNECT,
        # maxPoolSize=15,
        maxIdleTimeMS=1000*60*3,
    )
    
    db_list = {
        "autobracket": ["cbb_team", "player_season", "simulated_bracket", "simulation_dist", "simulation_run"],
        "backlogs": ["annuitydew", "backlog_game"],
        "mildredleague": ["ml_boxplot_transform", "ml_game", "ml_note", "ml_table_transform", "ml_team"],
        "quotes": ["quote"],
    }

    for database, collections in db_list.items():
        db = getattr(client, database)
        for collection in collections:
            current_coll = getattr(db, collection)
            data_list = await current_coll.find().to_list(length=99999999)
            print("test")
            data_df = pd.DataFrame(data_list)
            file_path = f"src/utils/backup_20210424/{str(database)}_{(collection)}.csv"
            data_df.to_csv(file_path)
    
    return


if __name__ == "__main__":
    asyncio.run(full_backup())
