import asyncio
import csv
from datetime import datetime
import os
from pathlib import Path
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from src.db.models import (
    QuoteORM,
    BacklogGameORM,
    MLGameORM,
    MLTeamORM,
    MLNoteORM,
    CBBTeamORM,
    PlayerSeasonORM,
    SimulationDistORM,
    SimulationRunORM,
    SimulatedBracketORM,
)
from src.db.startup import alchemy_startup

db_folder_path = Path("src/db")
db_backup_path = db_folder_path / "mongo_backup_20210427"


async def init_data_from_mongo():
    load_dotenv()
    # setting this env will return a connection engine from the startup function
    os.environ["INIT"] = "yes"

    engine = await alchemy_startup()

    with Session(engine) as session, open(
        db_backup_path / "quotes_quote.csv"
    ) as csv_file:
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

    with Session(engine) as session, open(
        db_backup_path / "backlogs_backlog_game.csv"
    ) as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[2:], row[2:]))
            # convert integer values. empty strings become null and strings become ints
            for field in ["game_hours", "game_minutes"]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = int(float(current_dict[field]))
            # convert boolean values. Y/Actual will become true, N/Estimate or blank becomes false
            for field in ["actual_playtime", "now_playing", "dlc"]:
                current_dict[field] = (current_dict[field] == "Y") or (
                    current_dict[field] == "Actual"
                )
            # convert date values from string. if empty, make null
            for field in ["add_date", "start_date", "beat_date", "complete_date"]:
                if current_dict[field]:
                    current_dict[field] = datetime.strptime(
                        current_dict[field], "%Y-%m-%d %H:%M:%S"
                    ).date()
                else:
                    current_dict[field] = None
            current_row = BacklogGameORM(**current_dict)
            print(current_row)
            session.add(current_row)

        # commit data to db
        session.commit()

    with Session(engine) as session, open(
        db_backup_path / "mildredleague_ml_game.csv"
    ) as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[2:], row[2:]))
            # convert integer values. empty strings become null and strings become ints
            for field in ["week_start", "week_end", "season", "playoff"]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = int(float(current_dict[field]))
            # convert float values. empty strings become null and strings become ints
            for field in ["away_score", "home_score"]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = float(current_dict[field])
            current_row = MLGameORM(**current_dict)
            print(current_row)
            session.add(current_row)

        # commit data to db
        session.commit()

    with Session(engine) as session, open(
        db_backup_path / "mildredleague_ml_team.csv"
    ) as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[2:], row[2:]))
            # convert integer values. empty strings become null and strings become ints
            for field in ["season", "playoff_rank"]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = int(float(current_dict[field]))
            # convert boolean values. "True" will become True
            for field in ["active"]:
                current_dict[field] = current_dict[field] == "True"
            current_row = MLTeamORM(**current_dict)
            print(current_row)
            session.add(current_row)

        # commit data to db
        session.commit()

    with Session(engine) as session, open(
        db_backup_path / "mildredleague_ml_note.csv"
    ) as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[2:], row[2:]))
            # convert integer values. empty strings become null and strings become ints
            for field in ["season"]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = int(float(current_dict[field]))
            current_row = MLNoteORM(**current_dict)
            print(current_row)
            session.add(current_row)

        # commit data to db
        session.commit()

    with Session(engine) as session, open(
        db_backup_path / "autobracket_cbb_team.csv"
    ) as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[1:], row[1:]))
            # convert integer values. empty strings become null and strings become ints
            for field in ["GlobalTeamID", "Rk", "W", "L"]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = int(float(current_dict[field]))
            # convert float values. empty strings become null and strings become floats
            for field in [
                "AdjEM",
                "AdjO",
                "AdjD",
                "AdjT",
                "Luck",
                "OppAdjEM",
                "OppO",
                "OppD",
                "NCAdjEM",
            ]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = float(current_dict[field])
            current_row = CBBTeamORM(**current_dict)
            print(current_row)
            session.add(current_row)

        # commit data to db
        session.commit()

    with Session(engine) as session, open(
        db_backup_path / "autobracket_player_season.csv"
    ) as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[1:], row[1:]))
            # convert integer values. empty strings become null and strings become ints
            for field in [
                "StatID",
                "TeamID",
                "PlayerID",
                "SeasonType",
                "Games",
                "Minutes",
                "FieldGoalsMade",
                "FieldGoalsAttempted",
                "TwoPointersMade",
                "TwoPointersAttempted",
                "FreeThrowsMade",
                "FreeThrowsAttempted",
                "OffensiveRebounds",
                "DefensiveRebounds",
                "Rebounds",
                "Assists",
                "Steals",
                "BlockedShots",
                "Turnovers",
                "PersonalFouls",
                "Points",
            ]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = int(float(current_dict[field]))
            # convert float values. empty strings become null and strings become floats
            for field in [
                "FantasyPoints",
                "FieldGoalsPercentage",
                "FantasyPointsFanDuel",
                "FantasyPointsDraftKings",
                "TwoPointersPercentage",
                "ThreePointersPercentage",
                "FreeThrowsPercentage",
                "two_attempt_chance",
                "two_chance",
                "three_chance",
                "ft_chance",
            ]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = float(current_dict[field])
            current_row = PlayerSeasonORM(**current_dict)
            print(current_row)
            session.add(current_row)

        # commit data to db
        session.commit()

    with Session(engine) as session, open(
        db_backup_path / "autobracket_simulation_dist.csv"
    ) as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[2:], row[2:]))
            # convert integer values. empty strings become null and strings become ints
            for field in [
                "max_margin_top",
                "max_margin_bottom",
                "medium_margin_top",
                "medium_margin_bottom",
                "mild_margin_top",
                "mild_margin_bottom",
                "median_margin_top",
                "median_margin_bottom",
                "median_margin",
            ]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = int(float(current_dict[field]))
            # convert float values. empty strings become null and strings become floats
            for field in [
                "home_win_chance_max",
                "home_win_chance_medium",
                "home_win_chance_mild",
                "home_win_chance_median",
            ]:
                if not current_dict[field]:
                    current_dict[field] = None
                else:
                    current_dict[field] = float(current_dict[field])
            current_row = SimulationDistORM(**current_dict)
            print(current_row)
            session.add(current_row)

        # commit data to db
        session.commit()

    with Session(engine) as session, open(
        db_backup_path / "autobracket_simulation_run.csv"
    ) as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[2:], row[2:]))
            current_row = SimulationRunORM(**current_dict)
            print(current_row)
            session.add(current_row)

        # commit data to db
        session.commit()

    with Session(engine) as session, open(
        db_backup_path / "autobracket_simulated_bracket.csv"
    ) as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            current_dict = dict(zip(headers[2:], row[2:]))
            current_row = SimulatedBracketORM(**current_dict)
            print(current_row)
            session.add(current_row)

        # commit data to db
        session.commit()

    print("Data restored!")


if __name__ == "__main__":
    asyncio.run(init_data_from_mongo())
