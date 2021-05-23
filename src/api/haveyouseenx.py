# import Python packages
import json
import os
from typing import List

# import third party packages
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import httpx
import numpy
import pandas
import plotly
import plotly.express as px
from sqlalchemy import select, and_
from sqlalchemy.future import Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql import func

# import custom local stuff
from src.api.security import validate_jwt
from src.db.alchemy import get_alchemy
from src.db.models import (
    GameStatus,
    BacklogGameORM,
    BacklogGame,
    BacklogGamePatch,
    BacklogUserVisualsORM,
    BacklogChartType,
)


hysx_api = APIRouter(
    prefix="/haveyouseenx",
    tags=["haveyouseenx"],
)


@hysx_api.get("/annuitydew/game/all")
async def get_all_games(engine: Engine = Depends(get_alchemy)):
    with Session(engine) as session:
        sql = select(BacklogGameORM)
        result = session.execute(sql).scalars().all()

    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="No data found!")


@hysx_api.post("/annuitydew/game", dependencies=[Depends(validate_jwt)])
async def add_games(
    row_list: List[BacklogGame],
    background_tasks: BackgroundTasks,
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        for row in row_list:
            # conversion from Pydantic model to ORM model
            session.add(BacklogGameORM(**row.dict()))
        session.commit()

    # need to update visualizations for this user in the background
    background_tasks.add_task(update_visualizations, engine=engine)

    return {
        "result": row_list,
    }


@hysx_api.get("/annuitydew/game/{id}", response_model=BacklogGame)
async def get_game(
    id: int,
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        sql = select(BacklogGameORM).where(BacklogGameORM.id == id)
        # one returns a Row object, which is a named tuple.
        # using scalar_one to access the object directly instead.
        try:
            result = session.execute(sql).scalar_one()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")

    return result


@hysx_api.patch("/annuitydew/game/{id}", dependencies=[Depends(validate_jwt)])
async def edit_game(
    id: int,
    patch: BacklogGamePatch,
    background_tasks: BackgroundTasks,
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        sql = select(BacklogGameORM).where(BacklogGameORM.id == id)
        # one returns a Row object, which is a named tuple.
        # using scalar_one to access the object directly instead.
        try:
            result = session.execute(sql).scalar_one()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")

        patch_dict = patch.dict(exclude_unset=True)
        for attr, value in patch_dict.items():
            setattr(result, attr, value)
        session.commit()
        session.refresh(result)

    # need to update visualizations for this user in the background
    background_tasks.add_task(update_visualizations, engine=engine)

    return {
        "result": result,
    }


@hysx_api.delete("/annuitydew/game/{id}", dependencies=[Depends(validate_jwt)])
async def delete_game(
    id: int,
    background_tasks: BackgroundTasks,
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        deletion = session.get(BacklogGameORM, id)
        if deletion is None:
            raise HTTPException(status_code=404, detail="No data found!")
        session.delete(deletion)
        session.commit()

    # need to update visualizations for this user in the background
    background_tasks.add_task(update_visualizations, engine=engine)

    return {
        "result": deletion,
    }


@hysx_api.get("/annuitydew/stats/counts")
async def count_by_status(engine: Engine = Depends(get_alchemy)):
    with Session(engine) as session:
        try:
            results = (
                session.query(
                    BacklogGameORM.game_status, func.count(BacklogGameORM.game_status)
                )
                .group_by(BacklogGameORM.game_status)
                .all()
            )
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")

    stats = {result[0]: result[1] for result in results}
    sorted_stats = dict(sorted(stats.items(), key=lambda item: item[1], reverse=True))
    return sorted_stats


@hysx_api.get("/annuitydew/stats/playtime")
async def playtime(engine: Engine = Depends(get_alchemy)):
    with Session(engine) as session:
        try:
            results = session.query(
                func.sum(BacklogGameORM.game_hours),
                func.sum(BacklogGameORM.game_minutes),
            ).one()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")

    # move chunks of 60 minutes into the hours count
    total_hours, total_minutes = results
    leftover_minutes = total_minutes % 60
    hours_to_move = (total_minutes - leftover_minutes) / 60
    total_hours = int(total_hours + hours_to_move)
    total_minutes = int(leftover_minutes)

    return {
        "total_hours": total_hours,
        "total_minutes": total_minutes,
    }


@hysx_api.get("/annuitydew/charts/{chart_type}")
async def get_backlog_user_visuals(
    chart_type: BacklogChartType,
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        sql = select(getattr(BacklogUserVisualsORM, f"{chart_type}_json")).where(
            BacklogUserVisualsORM.id == "annuitydew"
        )
        # one returns a Row object, which is a named tuple.
        # using scalar_one to access the object directly instead.
        try:
            result = session.execute(sql).scalar_one()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")

    return result


@hysx_api.get('/annuitydew/search', response_model=List[BacklogGame])
async def search(
    engine: Engine = Depends(get_alchemy),
    dlc: bool = None,
    now_playing: bool = None,
    game_status: GameStatus = None,
    q: str = None,
):
    initial_args = {
        'dlc': dlc,
        'now_playing': now_playing,
        'game_status': game_status,
    }
    final_args = { k:v for k, v in initial_args.items() if v is not None }
    if final_args:
        query_expression_list = [
            (getattr(BacklogGameORM, key)) == value for key, value in final_args.items()
        ]
        combined_query_expression = and_(*query_expression_list)
        filters = True
    else:
        filters = False
    # change to plain q for OR results. f"\"{q}\"" is an AND search.
    with Session(engine) as session:
        if filters:
            sql = select(BacklogGameORM).where(combined_query_expression)
        elif q == '' or q is None:
            sql = select(BacklogGameORM)
        else:
            sql = select(BacklogGameORM)

        try:
            result = session.execute(sql).scalars().all()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")

    return result


async def update_visualizations(engine: Engine = Depends(get_alchemy)):
    # make the necessary HTTPX requests
    async with httpx.AsyncClient() as client:
        domain = os.getenv('ADDRESS')
        backlog_data = await client.get(f"{domain}/haveyouseenx/annuitydew/game/all")
        count_data = await client.get(f"{domain}/haveyouseenx/annuitydew/stats/counts")

    # store json
    backlog_json = backlog_data.json()
    count_json = count_data.json()

    # update JSON for user visuals
    treemap_json = await pipeline_for_treemap(backlog_json)
    bubbles_json = await pipeline_for_bubbles(backlog_json)
    timeline_json = await pipeline_for_timeline(backlog_json, count_json)

    new_record = {
        "id": "annuitydew",
        "treemap_json": treemap_json,
        "bubbles_json": bubbles_json,
        "timeline_json": timeline_json,
    }

    # update latest JSON in the database
    # (or create it if it doesn't exist)
    with Session(engine) as session:
        sql = select(BacklogUserVisualsORM).where(BacklogUserVisualsORM.id == "annuitydew")
        try:
            result = session.execute(sql).scalar_one()
            for attr, value in new_record.items():
                setattr(result, attr, value)
        except NoResultFound:
            session.add(BacklogUserVisualsORM(**new_record))
        session.commit()
    
    return new_record


async def pipeline_for_treemap(backlog_json):
    # convert to pandas dataframe
    backlog = pandas.DataFrame(backlog_json)
    # read backlog and create a count column
    backlog["count"] = 1
    # column to serve as the root of the backlog
    backlog["backlog"] = "Backlog"
    # complete gametime calc
    backlog["game_hours"] = backlog["game_hours"] + (backlog["game_minutes"] / 60)

    # pivot table by gameSystem and gameStatus.
    # fill missing values with zeroes

    system_status_df = (
        backlog.groupby(
            by=[
                "backlog",
                "game_system",
                "game_status",
            ]
        )
        .agg(
            {
                "count": sum,
                "game_hours": sum,
            }
        )
        .reset_index()
    )

    figure = px.treemap(
        system_status_df,
        path=["backlog", "game_status", "game_system"],
        values="count",
        color=numpy.log10(system_status_df["game_hours"]),
        color_continuous_scale=px.colors.diverging.Spectral_r,
        hover_data=["game_hours"],
    )

    # update margins and colors
    figure.update_layout(
        margin=dict(l=10, r=0, t=10, b=10),
    )
    figure.layout.coloraxis.colorbar = dict(
        title="Hours",
        tickvals=[1.0, 2.0, 3.0],
        ticktext=[10, 100, 1000],
    )

    # convert to JSON for the web
    return json.loads(plotly.io.to_json(figure))


async def pipeline_for_bubbles(backlog_json):
    # convert to pandas dataframe
    backlog = pandas.DataFrame(backlog_json)
    # read backlog and create a count column
    backlog["count_dist"] = 1
    # complete gametime calc
    backlog["game_hours"] = backlog["game_hours"] + (backlog["game_minutes"] / 60)

    # pivot table by gameSystem and gameStatus.
    # fill missing values with zeroes
    system_status_df = backlog.groupby(by=["game_system", "game_status",]).agg(
        {
            "count_dist": sum,
            "game_hours": sum,
        }
    )

    # we also want the % in each category for each system
    # this code takes care of that
    system_totals = system_status_df.groupby(["game_system"]).agg({"count_dist": sum})
    normalized_df = system_status_df.div(system_totals, level="game_system")
    normalized_df["game_hours"] = system_status_df["game_hours"]
    normalized_df["total_count"] = system_status_df["count_dist"]

    # now reset index and prep the data for JS
    normalized_df.reset_index(inplace=True)

    # x data for each status
    x_data_counts = [
        normalized_df.loc[normalized_df.game_status == status].total_count.tolist()
        for status in normalized_df.game_status.unique().tolist()
    ]

    # y data for each status
    y_data_dist = [
        normalized_df.loc[normalized_df.game_status == status].count_dist.tolist()
        for status in normalized_df.game_status.unique().tolist()
    ]

    # z data for each status
    z_data_hours = [
        normalized_df.loc[normalized_df.game_status == status].game_hours.tolist()
        for status in normalized_df.game_status.unique().tolist()
    ]

    # systems for each status
    label_data = [
        normalized_df.loc[normalized_df.game_status == status].game_system.tolist()
        for status in normalized_df.game_status.unique().tolist()
    ]

    # categories
    bubble_names = normalized_df.game_status.unique().tolist()

    # list of hex color codes
    color_data = px.colors.qualitative.Bold

    return {
        "x_data_counts": x_data_counts,
        "y_data_dist": y_data_dist,
        "z_data_hours": z_data_hours,
        "bubble_names": bubble_names,
        "label_data": label_data,
        "color_data": color_data,
    }


async def pipeline_for_timeline(backlog_json, count_json):
    # convert to pandas dataframe
    backlog = pandas.DataFrame(backlog_json)
    # drop unused columns, move dates to x axis to create timeline
    # sort for most recent event at the top
    backlog = backlog[
        [
            "id",
            "game_title",
            "sub_title",
            "add_date",
            "start_date",
            "beat_date",
            "complete_date",
        ]
    ].melt(
        id_vars=["id", "game_title", "sub_title"],
        var_name="event_name",
        value_name="event_date",
    )

    # fill empty cells with the backlog's birth date
    backlog["event_date"] = backlog["event_date"].fillna(
        numpy.datetime64("2011-10-08T16:00:00")
    )

    # event date to datetime
    backlog.event_date = pandas.to_datetime(backlog.event_date, utc=True)

    # sort by date descending
    backlog.sort_values(
        ["event_date", "id", "event_name"], ascending=False, inplace=True
    )

    # reset index
    backlog.reset_index(inplace=True)

    # next, place current status counts in the first row.
    # then we'll be able to calculate the backlog at older
    # points in time using the timeline
    backlog["not_started"] = count_json.get("Not Started")
    backlog["started"] = count_json.get("Started")
    backlog["beaten"] = count_json.get("Beaten")
    backlog["completed"] = count_json.get("Completed")
    backlog = backlog.assign(ns=0, s=0, b=0, c=0)

    # initalize modifiers
    mod_ns, mod_s, mod_b, mod_c = 0, 0, 0, 0

    for row in backlog.itertuples():
        backlog.at[row.Index, "ns"] += mod_ns
        backlog.at[row.Index, "s"] += mod_s
        backlog.at[row.Index, "b"] += mod_b
        backlog.at[row.Index, "c"] += mod_c
        if row.event_name == "add_date":
            mod_ns += 1
        elif row.event_name == "start_date":
            mod_ns -= 1
            mod_s += 1
        elif row.event_name == "beat_date":
            mod_s -= 1
            mod_b += 1
        elif row.event_name == "complete_date":
            mod_b -= 1
            mod_c += 1

    # now recalculate the timeline values. this is our final data
    backlog["ns"] = backlog["not_started"] - backlog["ns"]
    backlog["s"] = backlog["started"] - backlog["s"]
    backlog["b"] = backlog["beaten"] - backlog["b"]
    backlog["c"] = backlog["completed"] - backlog["c"]

    # change sort to ascending and drop unnecessary columns
    # set index to event date
    backlog = backlog.sort_values(["event_date", "id", "event_name"], ascending=True)[
        ["event_date", "ns", "s", "b", "c"]
    ]

    # drop duplicate dates (keep last, that will be most recent)
    backlog.drop_duplicates(subset=["event_date"], keep="last", inplace=True)

    # set event date as datetime index and resample to daily
    # also drop the date column (it's the index now)
    # and convert back to integers (resample changes dtype)
    time_idx = pandas.DatetimeIndex(backlog.event_date)
    backlog.set_index(time_idx, inplace=True)
    backlog = backlog.resample("D").pad().drop(columns="event_date").convert_dtypes()

    # limit our chart to dates after the birth of the backlog
    backlog = backlog[
        pandas.Timestamp("2015-01-01 00:00:00+0000", tz="UTC", freq="D") :
    ]

    # x data is time, y_data is our timeline values
    y_data_c = [int(data_point) for data_point in backlog.c.tolist()]
    y_data_b = [int(data_point) for data_point in backlog.b.tolist()]
    y_data_s = [int(data_point) for data_point in backlog.s.tolist()]
    y_data_ns = [int(data_point) for data_point in backlog.ns.tolist()]
    x_data_dates = backlog.index.tolist()
    # dates need to be converted to be JS-ready
    x_data_dates = [
        int(time_point.strftime("%s%f")) / 1000 for time_point in x_data_dates
    ]

    # color data
    area_colors = px.colors.sequential.Agsunset[::2]

    return {
        "y_data_c": y_data_c,
        "y_data_b": y_data_b,
        "y_data_s": y_data_s,
        "y_data_ns": y_data_ns,
        "x_data_dates": x_data_dates,
        "area_colors": area_colors,
    }
