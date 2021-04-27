import asyncio
import csv
from datetime import datetime
import os
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from src.db.models import Base, QuoteORM, BacklogGameORM
from src.db.startup import alchemy_startup

db_folder_path = Path('src/db')
db_file_path = db_folder_path / 'db.sqlite'
db_backup_path = db_folder_path / 'mongo_backup'


async def init_from_mongo():
    load_dotenv()
    # setting this env will return a connection string from the startup function
    os.environ["INIT"] = "yes"

    engine = await alchemy_startup()

    # creates tables based on class definitions
    Base.metadata.create_all(engine)

    with Session(engine) as session, open(db_backup_path / 'quotes_quote.csv') as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[2:], row[2:]))
            current_row = QuoteORM(**current_dict)
            print(current_row)
            session.add(current_row)
        
        # commit data to db
        session.commit()

        # select it all back out for viewing
        sql = select(QuoteORM)
        result = session.execute(sql).scalars().all()
        print(result)

    with Session(engine) as session, open(db_backup_path / 'backlogs_backlog_game.csv') as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[2:], row[2:]))
            # convert integer values. empty strings become null and strings become ints
            for field in ['game_hours', 'game_minutes']:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = int(float(current_dict[field]))
            # convert boolean values. Y/Actual will become true, N/Estimate or blank becomes false
            for field in ['actual_playtime', 'now_playing', 'dlc']:
                current_dict[field] = ((current_dict[field] == 'Y') or (current_dict[field] == 'Actual'))
            # convert date values from string. if empty, make null
            for field in ['add_date', 'start_date', 'beat_date', 'complete_date']:
                if current_dict[field]:
                    current_dict[field] = datetime.strptime(current_dict[field], '%Y-%m-%d %H:%M:%S').date()
                else:
                    current_dict[field] = None
            current_row = BacklogGameORM(**current_dict)
            print(current_row)
            session.add(current_row)
        
        # commit data to db
        session.commit()

        # select it all back out for viewing
        sql = select(BacklogGameORM)
        result = session.execute(sql).scalars().all()
        print(result)


if __name__ == "__main__":
    asyncio.run(init_from_mongo())
