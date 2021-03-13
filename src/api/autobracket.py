# import native Python packages
from datetime import date
from enum import Enum
from math import floor
import multiprocessing
import pathlib
from typing import Dict
from odmantic.model import EmbeddedModel
import orjson
from time import perf_counter

# import third party packages
from fastapi import APIRouter, HTTPException, Depends, Path
from motor.motor_asyncio import AsyncIOMotorClient
import numpy as np
import pandas
from odmantic import AIOEngine, Field, Model, query
import requests
from scipy import stats
from sklearn.cluster import KMeans

# import custom local stuff
from instance.config import FANTASY_DATA_KEY_CBB, FANTASY_DATA_KEY_FREE
from src.db.atlas import get_odm
from src.api.security import validate_jwt


ab_api = APIRouter(
    prefix="/autobracket",
    tags=["autobracket"],
    # dependencies=[Depends(validate_jwt)],
)


class FantasyDataSeason(str, Enum):
    PRIORSEASON1 = "2020"
    CURRENTSEASON = "2021"


class BracketFlavor(str, Enum):
    NONE = "none"
    MILD = "mild"
    MEDIUM = "medium"
    MAX = "max"


class CBBTeam(Model):
    SeasonTeamID: str = Field(primary_field=True)
    Key: str
    School: str
    Name: str
    GlobalTeamID: int
    Conference: str
    TeamLogoUrl: str
    ShortDisplayName: str
    Stadium: Dict
    Season: str
    Rk: int
    Conf: str
    W: int
    L: int
    AdjEM: float
    AdjO: float
    AdjD: float
    AdjT: float
    Luck: float
    OppAdjEM: float
    OppO: float
    OppD: float
    NCAdjEM: float


class PlayerSeason(Model):
    StatID: int = Field(primary_field=True)
    TeamID: int
    PlayerID: int
    SeasonType: int
    Season: str
    Name: str
    Team: str
    Position: str
    Games: int
    FantasyPoints: float
    Minutes: int
    FieldGoalsMade: int
    FieldGoalsAttempted: int
    FieldGoalsPercentage: float
    TwoPointersMade: int
    TwoPointersAttempted: int
    ThreePointersMade: int
    ThreePointersAttempted: int
    FreeThrowsMade: int
    FreeThrowsAttempted: int
    OffensiveRebounds: int
    DefensiveRebounds: int
    Rebounds: int
    Assists: int
    Steals: int
    BlockedShots: int
    Turnovers: int
    PersonalFouls: int
    Points: int
    FantasyPointsFanDuel: float
    FantasyPointsDraftKings: float
    two_attempt_chance: float
    two_chance: float
    three_chance: float
    ft_chance: float


class GameSummary(EmbeddedModel):
    season: str
    away_key: str
    home_key: str
    neutral_site: bool
    home_margin: int
    total_possessions: int


class SimulationRun(Model):
    game_summary: GameSummary
    team_box_score: Dict
    full_box_score: Dict


class SimulationDist(Model):
    away_key: str
    home_key: str
    season: str
    home_win_chance_max: float
    max_margin_top: int
    max_margin_bottom: int
    home_win_chance_medium: float
    medium_margin_top: int
    medium_margin_bottom: int
    home_win_chance_mild: float
    mild_margin_top: int
    mild_margin_bottom: int
    home_win_chance_median: float
    median_margin_top: int
    median_margin_bottom: int


@ab_api.get("/stats/{season}/all")
async def get_season_players(
    season: FantasyDataSeason,
    client: AsyncIOMotorClient = Depends(get_odm),
):
    engine = AIOEngine(motor_client=client, database="autobracket")
    data = [
        player_season
        async for player_season in engine.find(
            PlayerSeason,
            (PlayerSeason.Season == season),
            sort=PlayerSeason.StatID,
        )
    ]

    if data:
        return data
    else:
        raise HTTPException(status_code=404, detail="No data found!")


@ab_api.get("/stats/{season}/{team}")
async def get_season_team_players(
    season: FantasyDataSeason,
    team: str,
    client: AsyncIOMotorClient = Depends(get_odm),
):
    engine = AIOEngine(motor_client=client, database="autobracket")
    data = [
        player_season
        async for player_season in engine.find(
            PlayerSeason,
            (PlayerSeason.Season == season) & (PlayerSeason.Team == team),
            sort=PlayerSeason.StatID,
        )
    ]

    if data:
        return data
    else:
        raise HTTPException(status_code=404, detail="No data found!")


@ab_api.get("/sim/{season}/kmeans")
async def k_means_players(
    season: FantasyDataSeason,
    client: AsyncIOMotorClient = Depends(get_odm),
):

    engine = AIOEngine(motor_client=client, database="autobracket")
    player_data = [
        player_season
        async for player_season in engine.find(
            PlayerSeason,
            (PlayerSeason.Season == season),
            sort=(PlayerSeason.Team, PlayerSeason.StatID),
        )
    ]

    player_df = pandas.DataFrame(
        [player_season.doc() for player_season in player_data]
    ).set_index(["Team", "PlayerID"])

    # calculate potential columns for clustering, drop others
    player_df["points_per_second"] = player_df["Points"] / player_df["Minutes"] / 60
    player_df["shots_per_second"] = (
        player_df["FieldGoalsAttempted"] / player_df["Minutes"] / 60
    )
    player_df["rebounds_per_second"] = player_df["Rebounds"] / player_df["Minutes"] / 60
    player_df["assists_per_second"] = player_df["Assists"] / player_df["Minutes"] / 60
    player_df["steals_per_second"] = player_df["Steals"] / player_df["Minutes"] / 60
    player_df["blocks_per_second"] = (
        player_df["BlockedShots"] / player_df["Minutes"] / 60
    )
    player_df["turnovers_per_second"] = (
        player_df["Turnovers"] / player_df["Minutes"] / 60
    )
    player_df["fouls_per_second"] = (
        player_df["PersonalFouls"] / player_df["Minutes"] / 60
    )

    # minutes distribution for histogram
    hist_data = player_df["Minutes"].values.tolist()

    # drop anyone that didn't play a minute
    player_df = player_df.loc[player_df["Minutes"] > 100]

    # work in progress, but these will be the columns to start with
    player_df = player_df[
        [
            "two_attempt_chance",
            "two_chance",
            "three_chance",
            "ft_chance",
            # "points_per_second",
            # "shots_per_second",
            # "rebounds_per_second",
            # "assists_per_second",
            # "steals_per_second",
            # "blocks_per_second",
            # "turnovers_per_second",
            # "fouls_per_second",
        ]
    ]

    # min-max normalization
    player_df = (player_df - player_df.min()) / (player_df.max() - player_df.min())

    # columns for the scatter plot (do this before adding labels to the data)
    scatter_cols = player_df.columns.tolist()

    # K-Means time! 10 pretty much looks like where the elbow tapers off,
    # when looking at the four "rate" variables.
    model = KMeans(n_clusters=10)
    model.fit(player_df)
    player_df["player_type"] = model.predict(player_df)

    # for now just display 1/10th of the data
    player_df = player_df.sample(
        frac=0.2,
        replace=False,
    )

    # remove outliers (these are probably folks with very few minutes anyway)
    player_df = player_df.loc[(np.abs(stats.zscore(player_df)) < 3).all(axis=1)]

    scatter_data = orjson.loads(player_df.to_json(orient="records"))

    return {
        "scatter_data": scatter_data,
        "scatter_columns": scatter_cols,
        "inertia": model.inertia_,
        "hist_data": hist_data,
    }


@ab_api.get("/bracket/{season}/{flavor}")
async def single_sim_bracket(
    season: FantasyDataSeason,
    flavor: BracketFlavor,
    client: AsyncIOMotorClient = Depends(get_odm),
):
    # first grab an empty bracket
    empty_bracket_df = pandas.read_csv(
        pathlib.Path("src/db/matchup_table_2021.csv"),
        index_col="game_id",
    ).convert_dtypes()

    # auto dtypes are mostly good, but home win chance needs to be a float
    empty_bracket_df["home_win_chance"] = pandas.to_numeric(
        empty_bracket_df["home_win_chance"], downcast="float"
    )
    engine = AIOEngine(motor_client=client, database="autobracket")
    distribution_data = [
        matchup.doc() async for matchup in engine.find(
            SimulationDist,
            (SimulationDist.season == season),
        )
    ]
    if not distribution_data:
        raise HTTPException(status_code=404, detail="No data found!")
    distribution_df = pandas.DataFrame(distribution_data)

    # set list of columns needed based on bracket options
    if flavor == BracketFlavor.NONE:
        needed_columns = ["home_win_chance_median", "median_margin_top", "median_margin_bottom"]
    elif flavor == BracketFlavor.MILD:
        needed_columns = [
            "home_win_chance_mild",
            "mild_margin_top",
            "mild_margin_bottom",
        ]
    elif flavor == BracketFlavor.MEDIUM:
        needed_columns = [
            "home_win_chance_medium",
            "medium_margin_top",
            "medium_margin_bottom",
        ]
    elif flavor == BracketFlavor.MAX:
        needed_columns = ["home_win_chance_max", "max_margin_top", "max_margin_bottom"]
    else:
        raise HTTPException(
            status_code=400, detail=f"Can't process this type of bracket! {flavor}"
        )

    # generate game outcomes
    rng = np.random.default_rng()
    empty_bracket_df["sim_reroll"] = rng.random(size=len(empty_bracket_df))

    # make necessary columns
    for column in needed_columns:
        empty_bracket_df[column] = 0.0

    # empty list for query data to be used later to pull box scores
    query_data = []

    for x in empty_bracket_df.index:
        away_key = empty_bracket_df.loc[x, "away_key"]
        home_key = empty_bracket_df.loc[x, "home_key"]
        away_school = empty_bracket_df.loc[x, "away_school"]
        home_school = empty_bracket_df.loc[x, "home_school"]
        away_seed = empty_bracket_df.loc[x, "away_seed"]
        home_seed = empty_bracket_df.loc[x, "home_seed"]
        advancing_location = empty_bracket_df.loc[x, "advance_to"]
        # bracket is home/away agnostic this year, so just filter for either combo
        filtered_df = distribution_df.loc[
            (
                (distribution_df.away_key == away_key)
                & (distribution_df.home_key == home_key)
            )
            | (
                (distribution_df.away_key == home_key)
                & (distribution_df.home_key == away_key)
            )
        ].copy()
        # make sure we're not pulling the inverted outcome
        if home_key == filtered_df.at[list(filtered_df.index)[0], "home_key"]:
            empty_bracket_df.loc[x, "home_win_chance"] = filtered_df.at[
                list(filtered_df.index)[0], needed_columns[0]
            ]
        else:
            empty_bracket_df.loc[x, "home_win_chance"] = (
                1 - filtered_df.at[list(filtered_df.index)[0], needed_columns[0]]
            )
        if (
            empty_bracket_df.at[x, "sim_reroll"]
            < empty_bracket_df.at[x, "home_win_chance"]
        ):
            game_winner = home_key
            winner_seed = home_seed
            winner_school = home_school
        else:
            game_winner = away_key
            winner_seed = away_seed
            winner_school = away_school

        # set the three dynamic columns so we can lookup a game later
        if home_key == filtered_df.at[list(filtered_df.index)[0], "home_key"]:
            empty_bracket_df.loc[x, needed_columns[0]] = filtered_df.at[
                list(filtered_df.index)[0], needed_columns[0]
            ]
            empty_bracket_df.loc[x, needed_columns[1]] = filtered_df.at[
                list(filtered_df.index)[0], needed_columns[1]
            ]
            empty_bracket_df.loc[x, needed_columns[2]] = filtered_df.at[
                list(filtered_df.index)[0], needed_columns[2]
            ]
        else:
            # flip values where the away tournament team is the home simulation team
            empty_bracket_df.loc[x, needed_columns[0]] = 1 - filtered_df.at[
                list(filtered_df.index)[0], needed_columns[0]
            ]
            # flip high and low values AND the sign
            empty_bracket_df.loc[x, needed_columns[1]] = -1 * filtered_df.at[
                list(filtered_df.index)[0], needed_columns[2]
            ]
            empty_bracket_df.loc[x, needed_columns[2]] = -1 * filtered_df.at[
                list(filtered_df.index)[0], needed_columns[1]
            ]

        # time to add query data for looking up box scores later
        if game_winner == home_key:
            home_margin_range_low = 0
            home_margin_range_high = empty_bracket_df.loc[x, needed_columns[1]]
        else:
            home_margin_range_low = empty_bracket_df.loc[x, needed_columns[2]]
            home_margin_range_high = 0

        query_expression_list_normal = [
            (SimulationRun.game_summary.away_key == away_key),
            (SimulationRun.game_summary.home_key == home_key),
            (SimulationRun.game_summary.home_margin >= home_margin_range_low),
            (SimulationRun.game_summary.home_margin <= home_margin_range_high),
        ]
        normal_query = query.and_(*query_expression_list_normal)
        # reversed version to find games where the home and away teams are flipped
        query_expression_list_reversed = [
            (SimulationRun.game_summary.away_key == home_key),
            (SimulationRun.game_summary.home_key == away_key),
            (SimulationRun.game_summary.home_margin >= (-1 * home_margin_range_high)),
            (SimulationRun.game_summary.home_margin <= (-1 * home_margin_range_low)),
        ]
        reversed_query = query.and_(*query_expression_list_reversed)
        combined_query = query.or_(normal_query, reversed_query)
        query_data.append(combined_query)

        # advance the winner to the next round, unless it's the title game. then it's over!
        empty_bracket_df.loc[x, "sim_winner"] = game_winner
        if advancing_location == 68:
            break
        else:
            if empty_bracket_df.at[advancing_location, "away_key"] == "TBD":
                empty_bracket_df.loc[advancing_location, "away_key"] = game_winner
                empty_bracket_df.loc[advancing_location, "away_seed"] = winner_seed
                empty_bracket_df.loc[advancing_location, "away_school"] = winner_school
            else:
                empty_bracket_df.loc[advancing_location, "home_key"] = game_winner
                empty_bracket_df.loc[advancing_location, "home_seed"] = winner_seed
                empty_bracket_df.loc[advancing_location, "home_school"] = winner_school

    # construct the query of all applicable box scores
    full_bracket_query = query.or_(*query_data)
    eligible_box_scores = await engine.find(
        SimulationRun,
        full_bracket_query,
    )
    box_score_data = [game.doc() for game in eligible_box_scores]
    box_score_game_summaries = [game["game_summary"] for game in box_score_data]
    # we need to convert objectid to string here. can't output objectid to json natively
    box_score_ids = [str(game["_id"]) for game in box_score_data]
    # index will be object IDs
    box_score_game_summary_df = pandas.DataFrame(box_score_game_summaries).set_index(
        ["away_key", "home_key"]
    )
    box_score_game_summary_df["sim_ObjectId"] = box_score_ids
    selected_box_scores = box_score_game_summary_df.groupby(level=[0, 1]).sample(n=1)

    # final returnable DF!
    bracket_df = empty_bracket_df.merge(selected_box_scores, left_on=["away_key", "home_key"], right_index=True, how="left")
    bracket_df_reversed = empty_bracket_df.merge(selected_box_scores, left_on=["home_key", "away_key"], right_index=True, how="left")
    bracket_df.update(bracket_df_reversed)

    # bracket to JSON
    bracket_json = orjson.loads(bracket_df.to_json(orient="records", default_handler=orjson.dumps))
    return bracket_json


@ab_api.get("/game/{season}/{away_key}/{home_key}/{flavor}")
async def single_sim_game(
    season: FantasyDataSeason,
    away_key: str,
    home_key: str,
    flavor: BracketFlavor,
    client: AsyncIOMotorClient = Depends(get_odm),
):
    # first grab game data and associated object IDs
    engine = AIOEngine(motor_client=client, database="autobracket")
    game_data = [
        [game.id, game.game_summary.home_margin]
        async for game in engine.find(
            SimulationRun,
            (
                (SimulationRun.game_summary.season == season)
                & (SimulationRun.game_summary.away_key == away_key)
                & (SimulationRun.game_summary.home_key == home_key)
            ),
            sort=(SimulationRun.game_summary.home_margin),
        )
    ]

    # convert to pandas dataframe and calculate quantiles
    game_df = pandas.DataFrame(game_data, columns=["ObjectId", "margin"])
    quantiles = game_df.quantile(q=[0.10, 0.25, 0.40, 0.60, 0.75, 0.90])
    # depending on what the user selected, filter the df for sampling
    if flavor == BracketFlavor.NONE:
        game_df = game_df.loc[
            game_df.margin.between(quantiles.loc[0.40][0], quantiles.loc[0.60][0])
        ]
    elif flavor == BracketFlavor.MILD:
        game_df = game_df.loc[
            game_df.margin.between(quantiles.loc[0.25][0], quantiles.loc[0.75][0])
        ]
    elif flavor == BracketFlavor.MEDIUM:
        game_df = game_df.loc[
            game_df.margin.between(quantiles.loc[0.10][0], quantiles.loc[0.90][0])
        ]

    # now sample a random game from the filtered data frame and query the DB for its full box score
    selected_game = game_df.sample(n=1).iat[0, 0]

    game_data = await engine.find_one(
        SimulationRun, (SimulationRun.id == selected_game)
    )

    return game_data


@ab_api.get("/sim/margins/{season}/{away_key}/{home_key}")
async def matchup_sim_margin(
    season: FantasyDataSeason,
    away_key: str,
    home_key: str,
    client: AsyncIOMotorClient = Depends(get_odm),
):

    engine = AIOEngine(motor_client=client, database="autobracket")
    margin_data = [
        game.game_summary.home_margin
        async for game in engine.find(
            SimulationRun,
            (
                (SimulationRun.game_summary.season == season)
                & (SimulationRun.game_summary.away_key == away_key)
                & (SimulationRun.game_summary.home_key == home_key)
            ),
            sort=(SimulationRun.game_summary.home_margin),
        )
    ]

    return margin_data


@ab_api.post(
    "/sim/{season}/{away_key}/{home_key}/{sample_size}/{preserve_size}",
)
async def full_game_simulation(
    season: FantasyDataSeason,
    away_key: str,
    home_key: str,
    sample_size: int = Path(..., gt=0, le=1000),
    preserve_size: int = Path(..., ge=10, le=100),
    client: AsyncIOMotorClient = Depends(get_odm),
):
    # performance timer
    start_time = perf_counter()

    engine = AIOEngine(motor_client=client, database="autobracket")
    matchup_data = [
        player_season
        async for player_season in engine.find(
            PlayerSeason,
            (PlayerSeason.Season == season)
            & ((PlayerSeason.Team == away_key) | (PlayerSeason.Team == home_key)),
            sort=(PlayerSeason.Team, PlayerSeason.StatID),
        )
    ]

    # create a dataframe representing one simulation
    matchup_df = pandas.DataFrame(
        [player_season.doc() for player_season in matchup_data]
    )
    # create an Away and Home field for identification in the simulation
    matchup_df["designation"] = "home"
    matchup_df.loc[matchup_df["Team"] == away_key, "designation"] = "away"

    # pull Kenpom tempo and EM data for the two teams
    kenpom_data = [
        team
        async for team in engine.find(
            CBBTeam,
            (CBBTeam.Season == season)
            & ((CBBTeam.Key == away_key) | (CBBTeam.Key == home_key)),
            sort=(CBBTeam.Key),
        )
    ]
    kenpom_df = pandas.DataFrame([team.doc() for team in kenpom_data])
    kenpom_tempo = kenpom_df.AdjT.sum()
    # we need some way to normalize for relative strength of teams/conferences, so one team
    # that plays in a weak conference doesn't get undue weight in the model.
    # I think we can achieve this with Kenpom's SOS AdjEM. Dividing by 100 gives us
    # a per-possession average point advantage / disadvantage.
    # This effect was still a little strong when applied to the RNG on a raw basis,
    # so we'll also divide it by about 5 to target the effect we want.
    home_strength = kenpom_df.loc[kenpom_df.Key == home_key, 'OppAdjEM'].item() / 100 / 5
    away_strength = kenpom_df.loc[kenpom_df.Key == away_key, 'OppAdjEM'].item() / 100 / 5

    # if multiprocessing, create a list of matchup dfs representing multiple simulations
    if False:
        cores_to_use = multiprocessing.cpu_count()
        simulations = [matchup_df.copy() for x in range(sample_size)]

        with multiprocessing.Pool(processes=cores_to_use) as p:
            results = p.map(run_simulation, simulations)
            # clean up
            p.close()
            p.join()
    else:
        # new array program is working!
        results, distribution = run_simulation(
            matchup_df, season, sample_size, preserve_size, kenpom_tempo, home_strength, away_strength
        )

    sim_time = perf_counter()

    writes = [SimulationRun(**doc) for doc in results] + [
        SimulationDist(**distribution)
    ]

    # write results to MongoDB
    await engine.save_all(writes)

    db_time = perf_counter()

    return {
        "success": "Check database for output!",
        "sim_time": (sim_time - start_time),
        "db_time": (db_time - sim_time),
        "simulations": sample_size,
    }


def run_simulation(matchup_df, season, sample_size, preserve_size, kenpom_tempo, home_strength, away_strength):
    # sort df by designation and playerID to guarantee order for later operations
    matchup_df.sort_values(by=["designation", "PlayerID"], inplace=True)

    # home and away dict
    home_away_dict = dict(matchup_df.groupby(["designation", "Team"]).size().index)
    # relative strength dict
    strength_dict = {
        home_away_dict["away"]: away_strength,
        home_away_dict["home"]: home_strength,
    }

    # new columns for simulated game stats
    sim_columns = [
        "sim_seconds",
        "sim_two_pointers_made",
        "sim_two_pointers_attempted",
        "sim_three_pointers_made",
        "sim_three_pointers_attempted",
        "sim_free_throws_made",
        "sim_free_throws_attempted",
        "sim_offensive_rebounds",
        "sim_defensive_rebounds",
        "sim_assists",
        "sim_steals",
        "sim_blocks",
        "sim_turnovers",
        "sim_fouls",
    ]
    for column in sim_columns:
        matchup_df[column] = 0

    # minutes for each player, divided by total minutes played for each team
    player_minute_totals = matchup_df.groupby(["Team", "PlayerID"]).agg(
        {"Minutes": "sum"}
    )
    team_minute_totals = matchup_df.groupby(["Team"]).agg({"Minutes": "sum"})
    player_time_share = player_minute_totals.div(
        team_minute_totals, level="Team"
    ).rename(columns={"Minutes": "minute_dist"})
    matchup_df = matchup_df.merge(
        player_time_share,
        left_on=["Team", "PlayerID"],
        right_index=True,
        how="left",
    )
    # minute weights will be used in the later step when we're selecting who's on the floor
    away_minute_weights = matchup_df.loc[
        matchup_df.designation == "away", ["PlayerID", "minute_dist"]
    ].to_numpy()
    home_minute_weights = matchup_df.loc[
        matchup_df.designation == "home", ["PlayerID", "minute_dist"]
    ].to_numpy()

    # new numpy random number generator
    rng = np.random.default_rng()

    # determine first possession in each game (simple 50/50 for now)
    matchup_list = team_minute_totals.index.to_list()
    # first row is who has the ball. second row indicates if possession will flip on
    # the next loop restart. third row makes a particular game "ineligible" for certain
    # future events in the loop (including when the game is over).
    # fourth row puts a game into a rebound situation.
    # fifth row puts a game into an assist situation.
    possession_status_array = np.array(
        [
            rng.integers(2, size=sample_size),
            np.zeros(sample_size),
            np.ones(sample_size),
            np.zeros(sample_size),
            np.zeros(sample_size),
        ],
        dtype=np.int8,
    )

    # game clock array, shot clock reset array, initialize possession length array,
    # possession counter for each team for each simulation
    time_remaining = np.array([60.0 * 40 for x in range(sample_size)])
    shot_clock_reset = np.ones(sample_size, dtype=np.int8)
    possession_length = np.zeros(sample_size)
    total_possessions = np.zeros(sample_size, dtype=np.int16)
    # normal mean 15 and stdev 4 yields about 140 possessions a game.
    # so let's adjust the normal dist mean by 140 / kenpomtempo
    # (this makes possessions longer if tempo is less than 140)
    tempo_factor = 140 / kenpom_tempo
    possession_length_mean = 15 * tempo_factor
    possession_length_stdev = 4 * tempo_factor

    # set index that will be the basis for updating box score.
    matchup_df.set_index(["Team", "PlayerID"], inplace=True)

    # expand the dataframe into X number of simulations. (prepend the index)
    # https://stackoverflow.com/questions/14744068/prepend-a-level-to-a-pandas-multiindex
    matchup_df = pandas.concat(
        [matchup_df.copy() for x in range(sample_size)],
        keys=[x for x in range(sample_size)],
        names=["simulation"],
    )

    # loop continues while any game is still ongoing
    while max(time_remaining) >= 0:
        # if there was a shot clock reset, this will add a possession to that particular game
        total_possessions += shot_clock_reset

        # who has the ball in each game?
        offensive_teams = [matchup_list[flag] for flag in possession_status_array[0, :]]
        defensive_teams = [
            matchup_list[1 - flag] for flag in possession_status_array[0, :]
        ]

        # array of relative strength values for application to the random number generators
        # for events
        offensive_strengths = [strength_dict[team] for team in offensive_teams]
        defensive_strengths = [strength_dict[team] for team in defensive_teams]

        # split df into games with time remaining and games with no time remaining
        # ongoing_games = [sim for sim, value in enumerate(time_remaining) if value > 0]
        games_to_resolve = [
            sim for sim, value in enumerate(time_remaining) if value <= 0
        ]
        # ongoing_games_df = matchup_df.loc[ongoing_games]
        # games_to_resolve_df = matchup_df.loc[games_to_resolve]

        # games to resolve might be over. calculate score and see if we need OT
        matchup_df["sim_points"] = (
            matchup_df["sim_free_throws_made"]
            + (matchup_df["sim_two_pointers_made"] * 2)
            + (matchup_df["sim_three_pointers_made"] * 3)
        )
        # aggregate team box score
        team_scores_df = matchup_df.groupby(level=[0, 1]).agg({"sim_points": "sum"})

        # compare score for each game to resolve. if tied, start overtime for that game
        for sim in games_to_resolve:
            if (
                team_scores_df.loc[(sim, offensive_teams[sim])][0]
                == team_scores_df.loc[(sim, defensive_teams[sim])][0]
            ):
                # start a 5 minute overtime!
                time_remaining[sim] = 60 * 5
            else:
                # game over array. this will prevent further simulation of a particular game
                possession_status_array[2, sim] = 0
                shot_clock_reset[sim] = 0

        # if there's no time left in any game, the loop ends.
        if time_remaining.sum() == 0:
            break

        # if there was a shot clock reset, we want to use the value from this array of fresh
        # random numbers from the normal distribution. otherwise, use a squished distribution
        # based on the previous possession's length.
        # we definitely need to pull in some sort of tempo per team here,
        # but for now let's aim for a mean of 140 possessions per game.
        fresh_possession_length = rng.normal(
            loc=possession_length_mean, scale=possession_length_stdev, size=sample_size
        )
        recycled_possession_length = rng.normal(
            loc=possession_length_mean * ((30 - possession_length) / 30),
            scale=possession_length_stdev * ((30 - possession_length) / 30),
            size=sample_size,
        )
        # determine whether or not we should use the fresh possession or recycled in each game.
        # we can do this by multiplying by the shot_clock_reset_array (or its inverse)
        fresh_possession_length *= shot_clock_reset
        recycled_possession_length *= 1 - shot_clock_reset

        # now add the two together to get the new possession length for each game
        # will either look like x+0 or 0+x for each row
        # cap the distribution at 29 seconds, so recycled distribution doesn't blow up
        # with a negative scale parameter
        possession_length = np.minimum(
            np.minimum((fresh_possession_length + recycled_possession_length), 29),
            time_remaining,
        )

        # pick 10 players for the current possession based on average time share
        # pandas has a bug so we're doing this with numpy now.
        away_team_sample = rng.choice(
            away_minute_weights[:, 0],
            size=5,
            replace=False,
            p=away_minute_weights[:, 1],
        )
        home_team_sample = rng.choice(
            home_minute_weights[:, 0],
            size=5,
            replace=False,
            p=home_minute_weights[:, 1],
        )

        on_floor_all_sims = np.array(
            [
                np.concatenate(
                    (
                        np.isin(
                            away_minute_weights[:, 0],
                            away_team_sample,
                        )
                        * 1,
                        np.isin(
                            home_minute_weights[:, 0],
                            home_team_sample,
                        )
                        * 1,
                    ),
                )
                for x in range(sample_size)
            ]
        ).flatten()

        matchup_df["player_on_floor"] = on_floor_all_sims
        # copy here to avoid a later settingwithcopywarning
        on_floor_df = matchup_df.loc[matchup_df.player_on_floor == 1].copy()
        # on_floor_df = matchup_df.groupby(level=[0, 1]).sample(
        #     n=5, replace=False, weights=matchup_df.minute_dist.to_list()
        # )

        # add the possession length to the time played for each individual on the floor and update.
        # numpy array is expanded 10x so each player of the 10 on the floor can get their time
        on_floor_df["sim_seconds"] += np.repeat(possession_length, 10)
        matchup_df.update(on_floor_df)

        # now, based on the 10 players on the floor, calculate probability of each event.
        # first, a steal check happens here. use steals per second over the season.
        # improvement: factor in the opponent's turnover statistics here.
        # steals per second times possession length to get the steal chance for this possession
        # times 2 assumes each team has the ball for about half the game. this effectively
        # converts steals per both teams' possession to steals per defensive possession (since
        # you can't get a steal while you're on offense!)
        # i think this is where we would put a tempo factor...
        steal_probs = steal_distribution(
            possession_length, defensive_teams, on_floor_df
        )

        # we also need turnover probabilities here
        turnover_probs = turnover_distribution(
            possession_length, offensive_teams, on_floor_df
        )

        # the steal/turnover check! we're modeling them as independent.
        # (right now it's possible that a turnover in a given possession
        # will always be a steal, if turnover_chance is less than steal_chance.)
        # we'll also not use prior probabilities in the turnover logic
        # for now, for this reason.
        # RNG is also where we'll apply relative team/conference strength.
        steal_turnover_success = rng.random(size=sample_size) - defensive_strengths
        team_steal_chances = (
            1 - steal_probs.groupby(level=0).prod()["no_steal_chance"].to_numpy()
        )
        team_turnover_chances = (
            1 - turnover_probs.groupby(level=0).prod()["no_turnover_chance"].to_numpy()
        )

        # if there's a successful steal, credit the steal and turnover, then flip possession.
        # games with steals don't do anything else until the loop restarts for a new possession.
        successful_steals = (
            steal_turnover_success < team_steal_chances
        ) * possession_status_array[2, :]
        steal_games = [sim for sim, value in enumerate(successful_steals) if value]
        successful_turnovers = (
            steal_turnover_success < team_turnover_chances
        ) * possession_status_array[2, :]
        turnover_games = [
            sim for sim, value in enumerate(successful_turnovers) if value
        ]

        # who got the steal in each game that had a steal?
        # pandas really needs to fix their groupby sampling...
        # let's try to reproduce the issue later with this commit, which worked:
        # https://github.com/AnnuityDew/tarpeydev/blob/ba344c7b29f3385caf5c964f10accc43ab600bd3/src/api/autobracket.py#L414
        # hypothesis is that it's because the resulting index is no longer unique.
        # but that can't be right because i duplicated the first index level
        # and tried to group from that as well.
        # for now we'll just have to keep sampling with numpy.
        # i'm really starting to wonder if it's because weights don't sum to one...
        steal_games_df = steal_probs.loc[steal_games]
        steal_games_numpy = steal_games_df.reset_index()[
            ["simulation", "Team", "PlayerID", "steal_chance"]
        ].to_numpy()
        turnover_games_df = turnover_probs.loc[turnover_games]
        turnover_games_numpy = turnover_games_df.reset_index()[
            ["simulation", "Team", "PlayerID", "turnover_chance"]
        ].to_numpy()

        # steal array has a 1 for the player in each steal game that got the steal
        steal_array = event_sampler(rng, steal_games_df, steal_games_numpy)
        turnover_array = event_sampler(rng, turnover_games_df, turnover_games_numpy)

        steal_games_df["sim_steals"] += steal_array
        turnover_games_df["sim_turnovers"] += turnover_array
        matchup_df.update(steal_games_df)
        matchup_df.update(turnover_games_df)

        # update the second row of possession status for turnover games to indicate
        # possession change
        np.put(possession_status_array[1, :], turnover_games, 1)
        # update third row to indicate end of loop for this game
        np.put(possession_status_array[2, :], turnover_games, 0)

        # if we've made it this far, there could be a non-shooting foul.
        # let's do foul logic here so we can be ready for both types
        # of fouls later. (no offensive fouls for now)
        # we also need to update and provide the given probability of
        # making it this far
        given_probabilities = 1 - team_turnover_chances
        foul_probs = foul_distribution(
            possession_length,
            defensive_teams,
            on_floor_df,
            given_probabilities,
        )

        # defensive foul check! (potential improvement, adding offensive fouls and
        # non-shooting fouls)
        # note that strength is ADDED here, not subtracted. this will make it more
        # likely that a weaker team commits a foul
        foul_occurred_rng = rng.random(size=sample_size) + defensive_strengths
        team_foul_chances = (
            1 - foul_probs.groupby(level=0).prod()["no_foul_chance"].to_numpy()
        )

        # fouls can't occur in games that are done with their loop.
        foul_occurrences = (
            foul_occurred_rng < team_foul_chances
        ) * possession_status_array[2, :]
        foul_games = [sim for sim, value in enumerate(foul_occurrences) if value]
        foul_games_df = foul_probs.loc[foul_games]
        foul_games_numpy = foul_games_df.reset_index()[
            ["simulation", "Team", "PlayerID", "foul_chance"]
        ].to_numpy()

        foul_array = event_sampler(rng, foul_games_df, foul_games_numpy)
        foul_games_df["sim_fouls"] += foul_array
        matchup_df.update(foul_games_df)

        # extra check here for games where it was a non-shooting foul (50/50 for now)
        non_shooting_foul_check = rng.integers(2, size=sample_size)
        # set allows us to check for a subset of foul games that were non-shooting fouls
        non_shooting_foul_games = list(
            set(foul_games).intersection(
                [sim for sim, value in enumerate(non_shooting_foul_check) if value]
            )
        )
        # we also need the list of shooting foul games so we can zero out the shot attempt and
        # not put the game into a rebound situation
        shooting_foul_games = list(
            set(foul_games).intersection(
                [sim for sim, value in enumerate(non_shooting_foul_check) if not value]
            )
        )
        # non-shooting foul games are marked ineligible for future events. next thing
        # for them will be a loop restart without change of possession.
        np.put(possession_status_array[2, :], non_shooting_foul_games, 0)
        # also need a separate array to identify shooting fouls so we can calculate # of free throws
        shooting_foul_occurrences = foul_occurrences
        np.put(shooting_foul_occurrences, non_shooting_foul_games, 0)
        shooting_foul_occurrences = np.repeat(shooting_foul_occurrences, 5)

        # time to model shot attempts. if there's no steal or turnover,
        # a shot is the only other outcome, so we can simply model who's
        # gonna take it and what kind of shot it will be.
        shot_probs = shot_distribution(offensive_teams, on_floor_df)

        # sample the shooter in each game
        shot_games_numpy = shot_probs.reset_index()[
            ["simulation", "Team", "PlayerID", "shot_share"]
        ].to_numpy()
        # multiply shooter array by possession status array expanded.
        # shot can't happen this possession in a game that had a steal/turnover
        # the "prior_shooter_array" is so later prior arrays don't break because
        # we filtered out some of the shooters that didn't get to shoot because
        # of a turnover
        prior_shooter_array = event_sampler(rng, shot_probs, shot_games_numpy)
        shooter_array = prior_shooter_array * np.repeat(
            possession_status_array[2, :], 5
        )
        two_chance_array = shot_probs.two_attempt_chance.to_numpy()

        # if a defensive player blocks, 50/50 chance to be a rebound.
        # using blocks per second over the season.
        # we're either crediting miss+block, or miss+block+rebound.
        block_probs = block_distribution(
            possession_length,
            defensive_teams,
            on_floor_df,
            given_probabilities,
        )

        # block check!
        block_success_rng = rng.random(size=sample_size) - defensive_strengths
        team_block_chances = (
            1 - block_probs.groupby(level=0).prod()["no_block_chance"].to_numpy()
        )

        # successful block can't happen in games that are done with their loop.
        # need to zero those out.
        successful_blocks = (
            block_success_rng < team_block_chances
        ) * possession_status_array[2, :]
        block_games = [sim for sim, value in enumerate(successful_blocks) if value]
        block_games_df = block_probs.loc[block_games]
        block_games_numpy = block_games_df.reset_index()[
            ["simulation", "Team", "PlayerID", "block_chance"]
        ].to_numpy()

        block_array = event_sampler(rng, block_games_df, block_games_numpy)
        block_games_df["sim_blocks"] += block_array
        matchup_df.update(block_games_df)

        # for any game with a block, there won't be a made shot or assist.
        np.put(possession_status_array[2, :], block_games, 0)

        # extra check here for games where the block went out of bounds
        block_inb_check = rng.integers(2, size=sample_size)
        # set allows us to check for a subset of block games that were blocks inb/oob
        block_inb_games = list(
            set(block_games).intersection(
                [sim for sim, value in enumerate(block_inb_check) if value]
            )
        )
        block_oob_games = list(
            set(block_games).intersection(
                [sim for sim, value in enumerate(block_inb_check) if not value]
            )
        )
        # the shot type check! we check shot type on a player basis, so need to expand the array x5
        two_or_three_rng = np.repeat(rng.random(size=sample_size), 5)
        # array of 2s, 3s, and 0s (includes those who would have shot if there wasn't a turnover)
        prior_attempted_shot_array = (
            (two_or_three_rng > two_chance_array) * 1 + 2
        ) * prior_shooter_array
        # filter out turnovers this possession to make this just who actually shot the ball
        attempted_shot_array = prior_attempted_shot_array * shooter_array

        # all block games are marked ineligible for future events. next thing
        # for most of them will be a loop restart.
        np.put(possession_status_array[2, :], block_games, 0)
        # here's the exception: block in-bounds games go to a rebound situation!
        np.put(possession_status_array[3, :], block_inb_games, 1)

        # add shot attempts for those that took shots
        two_attempt_array = np.where(attempted_shot_array == 2, 1, 0)
        three_attempt_array = np.where(attempted_shot_array == 3, 1, 0)
        shot_probs["sim_two_pointers_attempted"] += two_attempt_array
        shot_probs["sim_three_pointers_attempted"] += three_attempt_array

        # we need to prep for assist and foul calculation here. will involve Bayes,
        # so we need the components for probability of a successful shot
        # in this possession (1 minus everything that had to be dodged up
        # to this point). works as decrementing essentially because
        # the sequence of events isn't truly independent (i.e. if a turnover
        # happens in this model, a block will not because the loop restarts)
        given_probabilities = given_probabilities * (1 - team_block_chances)

        # time to see if the shots went in. this is a player check so expand array 5x
        shot_success_rng = np.repeat((rng.random(size=sample_size) - offensive_strengths), 5)
        # successful shots can't happen in games that are done with their loop.
        successful_twos = (
            two_attempt_array
            * (shot_success_rng < shot_probs["two_chance"].to_numpy())
            * np.repeat(possession_status_array[2, :], 5)
        )
        successful_threes = (
            three_attempt_array
            * (shot_success_rng < shot_probs["three_chance"].to_numpy())
            * np.repeat(possession_status_array[2, :], 5)
        )
        shot_probs["sim_two_pointers_made"] += successful_twos
        shot_probs["sim_three_pointers_made"] += successful_threes

        # this array will be 1 if there was a successful shot and a shooting foul."
        and_one_array = (shooting_foul_occurrences * successful_twos) + (
            shooting_foul_occurrences * successful_threes
        )
        two_fts_array = (
            shooting_foul_occurrences * (two_attempt_array - successful_twos)
        ) * 2
        three_fts_array = (
            shooting_foul_occurrences * (three_attempt_array - successful_threes)
        ) * 3
        ft_binomial_n = and_one_array + two_fts_array + three_fts_array
        made_ft_array = rng.binomial(
            n=ft_binomial_n,
            p=shot_probs["ft_chance"].to_numpy(),
        )

        shot_probs["sim_free_throws_attempted"] += ft_binomial_n
        shot_probs["sim_free_throws_made"] += made_ft_array

        # for made shots, update row 2 to flip possession for the next loop restart.
        # update row 5 because we will check for an assist.
        successful_shots = successful_twos + successful_threes
        successful_shot_games = [
            floor(sim / 5) for sim, value in enumerate(successful_shots) if value
        ]
        np.put(possession_status_array[1, :], successful_shot_games, 1)
        np.put(possession_status_array[4, :], successful_shot_games, 1)

        # for missed shots, update row three to mark game "ineligible" for future loop events
        # don't think this is even necessary though. update row four to put game into a rebound
        # situation.
        missed_shots = (two_attempt_array - successful_twos) + (
            three_attempt_array - successful_threes
        )
        missed_shot_games = [
            floor(sim / 5) for sim, value in enumerate(missed_shots) if value
        ]
        np.put(possession_status_array[2, :], missed_shot_games, 0)
        np.put(possession_status_array[3, :], missed_shot_games, 1)
        # extra array change here for games with a block that went out of bounds.
        # they can't go to a rebound situation
        np.put(possession_status_array[3, :], block_oob_games, 0)
        # extra array change here for games with a shooting foul. they can't go to a rebound situation
        # and for now we're assuming a change of possession, although at some point we'll need to add
        # rebound situation for missing the last free throw
        np.put(possession_status_array[3, :], shooting_foul_games, 0)
        np.put(possession_status_array[1, :], shooting_foul_games, 1)
        # we also need to subtract off the shot attempt if the missed shot was because of a shooting foul
        fouled_on_missed_two = np.zeros(sample_size, dtype=np.int8)
        np.put(fouled_on_missed_two, shooting_foul_games, 1)
        fouled_on_missed_two = (
            two_attempt_array * np.repeat(fouled_on_missed_two, 5) * missed_shots
        )
        fouled_on_missed_three = np.zeros(sample_size, dtype=np.int8)
        np.put(fouled_on_missed_three, shooting_foul_games, 1)
        fouled_on_missed_three = (
            three_attempt_array * np.repeat(fouled_on_missed_three, 5) * missed_shots
        )
        shot_probs["sim_two_pointers_attempted"] -= fouled_on_missed_two
        shot_probs["sim_three_pointers_attempted"] -= fouled_on_missed_three

        # update all shots attempted and made in the possession here!
        matchup_df.update(shot_probs)

        # time for assist logic. update given probabilities first.
        # the prior prob is a little different depending on whether a two or three was made
        shot_probs["attempted_shot_this_loop"] = prior_attempted_shot_array
        shot_probs["shot_success_this_loop"] = 0
        shot_probs.loc[
            shot_probs.attempted_shot_this_loop == 2, "shot_success_this_loop"
        ] = shot_probs.loc[shot_probs.attempted_shot_this_loop == 2, "two_chance"]
        shot_probs.loc[
            shot_probs.attempted_shot_this_loop == 3, "shot_success_this_loop"
        ] = shot_probs.loc[shot_probs.attempted_shot_this_loop == 3, "three_chance"]
        prior_made_shot_probs = shot_probs.loc[
            shot_probs.attempted_shot_this_loop > 0, "shot_success_this_loop"
        ].to_numpy()

        # start with assist logic after including prior probabilities
        given_probabilities = given_probabilities * prior_made_shot_probs

        assist_probs = assist_distribution(
            possession_length,
            offensive_teams,
            on_floor_df,
            given_probabilities,
        )
        assist_success_rng = rng.random(size=sample_size) - offensive_strengths
        team_assist_chances = (
            1 - assist_probs.groupby(level=0).prod()["no_assist_chance"].to_numpy()
        )
        # successful assists can only happen in games with successful shots
        successful_assists = (
            assist_success_rng < team_assist_chances
        ) * possession_status_array[4, :]
        assist_games = [sim for sim, value in enumerate(successful_assists) if value]
        assist_games_df = assist_probs.loc[assist_games]
        assist_games_numpy = assist_games_df.reset_index()[
            ["simulation", "Team", "PlayerID", "assist_chance"]
        ].to_numpy()

        assist_array = event_sampler(rng, assist_games_df, assist_games_numpy)
        assist_games_df["sim_assists"] += assist_array
        # add assists to the box score
        matchup_df.update(assist_games_df)

        # finally, need to decide rebound situations. who gets the rebound?
        (
            offensive_rebound_probs,
            defensive_rebound_probs,
            off_reb_chances,
        ) = rebound_distribution(offensive_teams, defensive_teams, on_floor_df)

        # rebound type check!
        off_reb_rng = rng.random(size=sample_size) - offensive_strengths
        team_off_reb_chances = off_reb_chances.groupby(level=0).max().to_numpy()

        # successful rebound can't happen in games that didn't go to a rebound situation.
        successful_off_rebs = (
            off_reb_rng < team_off_reb_chances
        ) * possession_status_array[3, :]
        successful_def_rebs = (
            off_reb_rng >= team_off_reb_chances
        ) * possession_status_array[3, :]

        off_reb_games = [sim for sim, value in enumerate(successful_off_rebs) if value]
        def_reb_games = [sim for sim, value in enumerate(successful_def_rebs) if value]

        # for games with a defensive rebound, need to indicate change of possession for next loop
        np.put(possession_status_array[1, :], def_reb_games, 1)

        off_reb_games_df = offensive_rebound_probs.loc[off_reb_games]
        def_reb_games_df = defensive_rebound_probs.loc[def_reb_games]
        off_reb_games_numpy = off_reb_games_df.reset_index()[
            ["simulation", "Team", "PlayerID", "off_reb_share"]
        ].to_numpy()
        def_reb_games_numpy = def_reb_games_df.reset_index()[
            ["simulation", "Team", "PlayerID", "def_reb_share"]
        ].to_numpy()

        # sample who got the offensive or defensive rebound in each game, then add to box score
        off_reb_array = event_sampler(rng, off_reb_games_df, off_reb_games_numpy)
        def_reb_array = event_sampler(rng, def_reb_games_df, def_reb_games_numpy)
        off_reb_games_df["sim_offensive_rebounds"] += off_reb_array
        def_reb_games_df["sim_defensive_rebounds"] += def_reb_array
        matchup_df.update(off_reb_games_df)
        matchup_df.update(def_reb_games_df)

        # update clocks in all games
        time_remaining -= possession_length
        # change possession in all games where there was a possession change
        possession_status_array[0, :] += possession_status_array[1, :]
        possession_status_array[0, :] = np.where(
            possession_status_array[0, :] == 2, 0, possession_status_array[0, :]
        )

        # shot clock reset array needs the values from row two (possession flip)
        shot_clock_reset = possession_status_array[1, :].copy()
        # reset all games for the next loop
        possession_status_array[1, :] = 0
        possession_status_array[2, :] = 1
        possession_status_array[3, :] = 0
        possession_status_array[4, :] = 0
        continue

    # that's the end of the loop.
    # time to set up the box scores!
    box_score_df = matchup_df[
        [
            "Name",
            "Position",
            "sim_seconds",
            "sim_two_pointers_made",
            "sim_two_pointers_attempted",
            "sim_three_pointers_made",
            "sim_three_pointers_attempted",
            "sim_free_throws_made",
            "sim_free_throws_attempted",
            "sim_offensive_rebounds",
            "sim_defensive_rebounds",
            "sim_assists",
            "sim_steals",
            "sim_blocks",
            "sim_turnovers",
            "sim_fouls",
            "sim_points",
        ]
    ]

    # calculate totals and downcast to ints
    box_score_df = box_score_df.assign(
        sim_minutes=lambda x: x.sim_seconds / 60
    ).convert_dtypes()

    # aggregate team box score and downcast to ints
    team_box_score_df = box_score_df.groupby(level=[0, 1]).sum().convert_dtypes()

    # multiindex slice to get the margin per simulation
    idx = pandas.IndexSlice
    team_box_score_df.loc[idx[:, home_away_dict["home"], :], "sim_points"].droplevel(
        "Team"
    )
    margins = team_box_score_df.loc[
        idx[:, home_away_dict["home"], :], "sim_points"
    ].droplevel("Team") - team_box_score_df.loc[
        idx[:, home_away_dict["away"], :], "sim_points"
    ].droplevel(
        "Team"
    )

    print("model doesn't currently account for rebound situation on a missed last ft")

    # preserve a subset of runs that will actually be persisted to the database.
    # if we run into errors it's probably the interpolation that needs further examination.
    quantiles = np.linspace(0, 1, preserve_size)
    margins_to_save = margins.quantile(q=quantiles, interpolation="nearest").to_numpy()
    games_to_save = []
    for margin in margins_to_save:
        selected_game = rng.choice(np.array(margins.index[margins == margin]))
        games_to_save.append(selected_game)

    # build the format of results for database input
    results_array = [
        {
            "game_summary": {
                "season": season.value,
                "away_key": home_away_dict["away"],
                "home_key": home_away_dict["home"],
                "neutral_site": True,
                "home_margin": int(margins[sim]),
                "total_possessions": int(total_possessions[sim]),
            },
            "team_box_score": orjson.loads(
                team_box_score_df.loc[sim].to_json(orient="index")
            ),
            "full_box_score": orjson.loads(
                box_score_df.loc[sim].to_json(orient="index")
            ),
        }
        for sim in games_to_save
    ]

    # to lighten the load on the DB, we'll preserve the simulation distribution.
    # this will be a way to avoid pulling tons of data for each bracket request
    user_breakpoints = margins.quantile(
        q=[0.00, 0.10, 0.25, 0.40, 0.60, 0.75, 0.90, 1.00], interpolation="nearest"
    )
    home_win_chance_max = len(margins.loc[margins > 0]) / len(margins)
    home_win_chance_medium = len(
        margins.loc[(user_breakpoints[0.90] >= margins) & (margins >= user_breakpoints[0.10]) & (margins > 0)]
    ) / len(
        margins.loc[
            (user_breakpoints[0.90] >= margins) & (margins >= user_breakpoints[0.10])
        ]
    )
    home_win_chance_mild = len(
        margins.loc[(user_breakpoints[0.75] >= margins) & (margins >= user_breakpoints[0.25]) & (margins > 0)]
    ) / len(
        margins.loc[
            (user_breakpoints[0.75] >= margins) & (margins >= user_breakpoints[0.25])
        ]
    )
    home_win_chance_median = len(
        margins.loc[(user_breakpoints[0.60] >= margins) & (margins >= user_breakpoints[0.40]) & (margins > 0)]
    ) / len(
        margins.loc[
            (user_breakpoints[0.60] >= margins) & (margins >= user_breakpoints[0.40])
        ]
    )

    distribution_data = {
        "away_key": home_away_dict["away"],
        "home_key": home_away_dict["home"],
        "season": season.value,
        "home_win_chance_max": home_win_chance_max,
        "max_margin_top": user_breakpoints[1.00],
        "max_margin_bottom": user_breakpoints[0.00],
        "home_win_chance_medium": home_win_chance_medium,
        "medium_margin_top": user_breakpoints[0.90],
        "medium_margin_bottom": user_breakpoints[0.10],
        "home_win_chance_mild": home_win_chance_mild,
        "mild_margin_top": user_breakpoints[0.75],
        "mild_margin_bottom": user_breakpoints[0.25],
        "home_win_chance_median": home_win_chance_median,
        "median_margin_top": user_breakpoints[0.60],
        "median_margin_bottom": user_breakpoints[0.40],
    }

    return results_array, distribution_data


def event_sampler(rng, games_df, games_numpy):
    try:
        event_array = (
            np.array(
                [
                    np.isin(
                        games_numpy[x : x + 5, 2],
                        rng.choice(
                            games_numpy[x : x + 5, 2],
                            size=1,
                            replace=False,
                            p=(games_numpy[0:5, 3] / games_numpy[0:5, 3].sum()).astype(
                                float
                            ),
                        ),
                    )
                    for x in range(0, len(games_df), 5)
                ]
            ).flatten()
            * 1
        )
    except ValueError:
        print("uh oh!")
        raise
    return event_array


def assist_distribution(
    possession_length, offensive_teams, on_floor_df, successful_shot_prob
):
    assist_fields = [
        "Assists",
        "Minutes",
        "sim_assists",
    ]
    # dropping the PlayerID level allows us to slice out only the teams on offense in each sim.
    offensive_index = [(sim, team) for sim, team in enumerate(offensive_teams)]
    assist_probs = on_floor_df.loc[
        on_floor_df.index.droplevel("PlayerID").isin(offensive_index), assist_fields
    ]
    # alternative...let's try truly modeling as an exponential distribution.
    # first calculate rate parameter (per game estimate)
    assist_probs["assist_chance_exp_theta"] = 1 / (
        2 * assist_probs["Assists"] / assist_probs["Minutes"] / 60
    )
    # now use rate parameter to calculate CDF per player, per possession.
    # x = the percentage of the team's gametime that has elapsed
    # numpy array is expanded 5x so each player of the 5 on this side can get their time
    assist_probs["no_assist_chance_prior"] = np.e ** (
        -1 * np.repeat(possession_length, 5) / assist_probs["assist_chance_exp_theta"]
    )
    # we could also randomly sample an exponential for each player using numpy
    # and see if it's less than the number of possession_seconds. might be
    # interesting to see how this changes the simulation.
    assist_probs["assist_chance_prior"] = 1 - assist_probs["no_assist_chance_prior"]

    # we need to do some bayes here to handle assists properly! everything
    # up to this point was modeled as independent, but assists can only happen
    # given a made shot. So we calculate P(assist|made shot) here.
    assist_probs["assist_chance"] = assist_probs["assist_chance_prior"] / np.repeat(
        successful_shot_prob, 5
    )
    assist_probs["no_assist_chance"] = 1 - assist_probs["assist_chance"]

    # if successful_shot_prob was zero, we'll have some infinite values in our dataframe.
    # this replaces them with 1s and 0s
    assist_probs.replace(np.inf, 1, inplace=True)
    assist_probs.replace(-np.inf, 0, inplace=True)

    return assist_probs


def foul_distribution(
    possession_length, defensive_teams, on_floor_df, attempted_shot_prob
):
    foul_fields = [
        "PersonalFouls",
        "Minutes",
        "sim_fouls",
    ]
    # dropping the PlayerID level allows us to slice out only the teams on defense in each sim.
    defensive_index = [(sim, team) for sim, team in enumerate(defensive_teams)]
    foul_probs = on_floor_df.loc[
        on_floor_df.index.droplevel("PlayerID").isin(defensive_index), foul_fields
    ]

    # the x2 factor is still here for fouls, even though you can foul on offense or defense.
    # but for now this model is assuming you can only foul on defense. we would scrap
    # this factor once we're modeling offensive fouls independently

    # let's try truly modeling as an exponential distribution.
    # first calculate rate parameter (1 / theta or beta), aka
    # (1 / average amount of seconds between two events)
    # factor of 2 because you can only steal
    # when you're playing on defense!
    foul_probs["foul_chance_exp_theta"] = 1 / (
        2 * foul_probs["PersonalFouls"] / foul_probs["Minutes"] / 60
    )
    # now use rate parameter to calculate CDF per player, per possession.
    # x = the percentage of the team's gametime that has elapsed
    # numpy array is expanded 5x so each player of the 5 on this side can get their time
    foul_probs["no_foul_chance_prior"] = np.e ** (
        -1 * np.repeat(possession_length, 5) / foul_probs["foul_chance_exp_theta"]
    )
    # we could also randomly sample an exponential for each player using numpy
    # and see if it's less than the number of possession_seconds. might be
    # interesting to see how this changes the simulation.
    foul_probs["foul_chance_prior"] = 1 - foul_probs["no_foul_chance_prior"]

    # we need to do some bayes here to handle fouls properly! everything
    # up to this point was modeled as independent, but fouls can only happen
    # given a made shot. So we calculate P(foul|made shot) here.
    foul_probs["foul_chance"] = foul_probs["foul_chance_prior"] / np.repeat(
        attempted_shot_prob, 5
    )
    foul_probs["no_foul_chance"] = 1 - foul_probs["foul_chance"]

    return foul_probs


def block_distribution(
    possession_length, defensive_teams, on_floor_df, no_turnover_prob
):
    block_fields = ["BlockedShots", "Minutes", "sim_blocks"]
    # dropping the PlayerID level allows us to slice out only the teams on defense in each sim.
    defensive_index = [(sim, team) for sim, team in enumerate(defensive_teams)]
    block_probs = on_floor_df.loc[
        on_floor_df.index.droplevel("PlayerID").isin(defensive_index), block_fields
    ]

    # let's try truly modeling as an exponential distribution.
    # first calculate rate parameter (1 / theta or beta), aka
    # (1 / average amount of seconds between two events)
    # factor of 2 because you can only steal
    # when you're playing on defense!
    block_probs["block_chance_exp_theta"] = 1 / (
        2 * block_probs["BlockedShots"] / block_probs["Minutes"] / 60
    )
    # now use rate parameter to calculate CDF per player, per possession.
    # x = the percentage of the team's gametime that has elapsed
    # numpy array is expanded 5x so each player of the 5 on this side can get their time
    block_probs["no_block_chance_prior"] = np.e ** (
        -1 * np.repeat(possession_length, 5) / block_probs["block_chance_exp_theta"]
    )
    # we could also randomly sample an exponential for each player using numpy
    # and see if it's less than the number of possession_seconds. might be
    # interesting to see how this changes the simulation.
    block_probs["block_chance_prior"] = 1 - block_probs["no_block_chance_prior"]

    # we need to do some bayes here to handle blocks properly! blocks can
    # only happen in our model given no turnover. so we calculate
    # P(block|no turnover) here.
    block_probs["block_chance"] = block_probs["block_chance_prior"] / np.repeat(
        no_turnover_prob, 5
    )
    block_probs["no_block_chance"] = 1 - block_probs["block_chance"]

    return block_probs


def shot_distribution(offensive_teams, on_floor_df):
    shot_fields = [
        "two_attempt_chance",
        "two_chance",
        "three_chance",
        "ft_chance",
        "TwoPointersAttempted",
        "TwoPointersMade",
        "ThreePointersAttempted",
        "ThreePointersMade",
        "FieldGoalsAttempted",
        "FieldGoalsMade",
        "FreeThrowsAttempted",
        "FreeThrowsMade",
        "sim_two_pointers_made",
        "sim_two_pointers_attempted",
        "sim_three_pointers_made",
        "sim_three_pointers_attempted",
        "sim_free_throws_made",
        "sim_free_throws_attempted",
    ]
    # dropping the PlayerID level allows us to slice out only the teams on offense in each sim.
    offensive_index = [(sim, team) for sim, team in enumerate(offensive_teams)]
    shot_probs = on_floor_df.loc[
        on_floor_df.index.droplevel("PlayerID").isin(offensive_index), shot_fields
    ]
    group_totals = shot_probs.groupby(level=[0, 1]).transform(np.sum)[
        ["FieldGoalsAttempted"]
    ]
    shot_share = shot_probs[["FieldGoalsAttempted"]].div(group_totals)
    shot_probs["shot_share"] = shot_share["FieldGoalsAttempted"]

    return shot_probs


def steal_distribution(possession_length, defensive_teams, on_floor_df):
    steal_fields = [
        "Steals",
        "Minutes",
        "sim_steals",
    ]
    # dropping the PlayerID level allows us to slice out only the teams on defense in each sim.
    defensive_index = [(sim, team) for sim, team in enumerate(defensive_teams)]
    steal_probs = on_floor_df.loc[
        on_floor_df.index.droplevel("PlayerID").isin(defensive_index), steal_fields
    ]
    # let's try truly modeling as an exponential distribution.
    # first calculate rate parameter (1 / theta or beta), aka
    # (1 / average amount of seconds between two events)
    # factor of 2 because you can only steal
    # when you're playing on defense!
    steal_probs["steal_chance_exp_theta"] = 1 / (
        2 * steal_probs["Steals"] / steal_probs["Minutes"] / 60
    )
    # now use rate parameter to calculate CDF per player, per possession.
    # x = the percentage of the team's gametime that has elapsed
    # numpy array is expanded 5x so each player of the 5 on this side can get their time
    steal_probs["no_steal_chance"] = np.e ** (
        -1 * np.repeat(possession_length, 5) / steal_probs["steal_chance_exp_theta"]
    )
    # we could also randomly sample an exponential for each player using numpy
    # and see if it's less than the number of possession_seconds. might be
    # interesting to see how this changes the simulation.
    steal_probs["steal_chance"] = 1 - steal_probs["no_steal_chance"]

    return steal_probs


def turnover_distribution(possession_length, offensive_teams, on_floor_df):
    turnover_fields = [
        "Turnovers",
        "Minutes",
        "sim_turnovers",
    ]
    # dropping the PlayerID level allows us to slice out only the teams on offensive in each sim.
    offensive_index = [(sim, team) for sim, team in enumerate(offensive_teams)]
    turnover_probs = on_floor_df.loc[
        on_floor_df.index.droplevel("PlayerID").isin(offensive_index), turnover_fields
    ]
    # let's try truly modeling as an exponential distribution.
    # first calculate rate parameter (1 / theta or beta), aka
    # (1 / average amount of seconds between two events)
    # factor of 2 because you can only steal
    # when you're playing on defense!
    turnover_probs["turnover_chance_exp_theta"] = 1 / (
        2 * turnover_probs["Turnovers"] / turnover_probs["Minutes"] / 60
    )
    # now use rate parameter to calculate CDF per player, per possession.
    # x = the percentage of the team's gametime that has elapsed
    # numpy array is expanded 5x so each player of the 5 on this side can get their time
    turnover_probs["no_turnover_chance"] = np.e ** (
        -1
        * np.repeat(possession_length, 5)
        / turnover_probs["turnover_chance_exp_theta"]
    )
    # we could also randomly sample an exponential for each player using numpy
    # and see if it's less than the number of possession_seconds. might be
    # interesting to see how this changes the simulation.
    turnover_probs["turnover_chance"] = 1 - turnover_probs["no_turnover_chance"]

    return turnover_probs


def rebound_distribution(offensive_teams, defensive_teams, on_floor_df):
    off_reb_fields = ["OffensiveRebounds", "sim_offensive_rebounds"]
    def_reb_fields = ["DefensiveRebounds", "sim_defensive_rebounds"]

    # dropping the PlayerID level allows us to slice out only the teams on each side in each sim.
    offensive_index = [(sim, team) for sim, team in enumerate(offensive_teams)]
    defensive_index = [(sim, team) for sim, team in enumerate(defensive_teams)]
    offensive_rebound_probs = on_floor_df.loc[
        on_floor_df.index.droplevel("PlayerID").isin(offensive_index), off_reb_fields
    ]
    defensive_rebound_probs = on_floor_df.loc[
        on_floor_df.index.droplevel("PlayerID").isin(defensive_index), def_reb_fields
    ]

    team_off_reb_totals = offensive_rebound_probs.groupby(level=[0, 1]).transform(
        np.sum
    )
    team_def_reb_totals = defensive_rebound_probs.groupby(level=[0, 1]).transform(
        np.sum
    )
    rebound_denominators = (
        team_off_reb_totals["OffensiveRebounds"].to_numpy()
        + team_def_reb_totals["DefensiveRebounds"].to_numpy()
    )

    # calculate each player's share of their team's rebounds
    off_reb_share = offensive_rebound_probs.div(team_off_reb_totals)
    offensive_rebound_probs["off_reb_share"] = off_reb_share["OffensiveRebounds"]
    def_reb_share = defensive_rebound_probs.div(team_def_reb_totals)
    defensive_rebound_probs["def_reb_share"] = def_reb_share["DefensiveRebounds"]

    off_reb_chances = team_off_reb_totals["OffensiveRebounds"] / rebound_denominators

    return (
        offensive_rebound_probs,
        defensive_rebound_probs,
        off_reb_chances,
    )


@ab_api.get("/FantasyDataRefresh/PlayerGameDay/{game_year}/{game_month}/{game_day}")
async def refresh_fd_player_games(
    game_year: int,
    game_month: int,
    game_day: int,
    client: AsyncIOMotorClient = Depends(get_odm),
):
    try:
        game_date = date(game_year, game_month, game_day)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"API error: {e}")

    requested_date = game_date.strftime("%Y-%b-%d")

    r = requests.get(
        f"https://api.sportsdata.io/api/cbb/fantasy/json/PlayerGameStatsByDate/{requested_date}"
        + "?key="
        + FANTASY_DATA_KEY_FREE
    )

    engine = AIOEngine(motor_client=client, database="autobracket")

    return {"message": "Mongo refresh complete!"}


@ab_api.get("/FantasyDataRefresh/PlayerSeason/{season}")
async def refresh_fd_player_season(
    season: FantasyDataSeason,
    client: AsyncIOMotorClient = Depends(get_odm),
):
    r = requests.get(
        f"https://api.sportsdata.io/api/cbb/fantasy/json/PlayerSeasonStats/{season}"
        + "?key="
        + FANTASY_DATA_KEY_CBB
    )

    engine = AIOEngine(motor_client=client, database="autobracket")

    # data manipulation is easier in Pandas!
    player_season_df = pandas.DataFrame(r.json())

    # season should be string (ex: 2020POST). then convert other columns.
    # if we do the opposite order the Season column will throw an error.
    # can't go directly from int to str - you'll get an error! map first
    player_season_df["Season"] = player_season_df["Season"].map(str).astype("string")
    player_season_df = player_season_df.convert_dtypes()

    # position is None for about 3200 players...fill with "Not Found"
    player_season_df["Position"] = player_season_df["Position"].fillna("Not Found")

    # renaming a few fields - we're going to overwrite them with more exact percentages next step
    player_season_df.rename(
        columns={
            "TwoPointersPercentage": "two_chance",
            "ThreePointersPercentage": "three_chance",
            "FreeThrowsPercentage": "ft_chance",
        },
        inplace=True,
    )

    # (re-)calculated fields for use in analysis. need to cast to float for division
    # to work properly, then fillna with zero
    player_season_df["two_attempt_chance"] = (
        pandas.to_numeric(player_season_df["TwoPointersAttempted"], downcast="float")
        / pandas.to_numeric(player_season_df["FieldGoalsAttempted"], downcast="float")
    ).fillna(0)
    player_season_df["two_chance"] = (
        pandas.to_numeric(player_season_df["TwoPointersMade"], downcast="float")
        / pandas.to_numeric(player_season_df["TwoPointersAttempted"], downcast="float")
    ).fillna(0)
    player_season_df["three_chance"] = (
        pandas.to_numeric(player_season_df["ThreePointersMade"], downcast="float")
        / pandas.to_numeric(
            player_season_df["ThreePointersAttempted"], downcast="float"
        )
    ).fillna(0)
    player_season_df["ft_chance"] = (
        pandas.to_numeric(player_season_df["FreeThrowsMade"], downcast="float")
        / pandas.to_numeric(player_season_df["FreeThrowsAttempted"], downcast="float")
    ).fillna(0)

    # back to json for writing to DB
    p = orjson.loads(player_season_df.to_json(orient="records"))
    await engine.save_all([PlayerSeason(**doc) for doc in p])

    return {"message": "Mongo refresh complete!"}


@ab_api.get("/FantasyDataRefresh/PlayerSeasonTeam/{season}/{team}")
async def refresh_fd_player_season_team(
    season: FantasyDataSeason,
    team: str,
):
    r = requests.get(
        f"https://api.sportsdata.io/api/cbb/fantasy/json/PlayerSeasonStatsByTeam/{season}/{team}"
        + "?key="
        + FANTASY_DATA_KEY_FREE
    )

    return {"message": "Mongo refresh complete!"}


@ab_api.get("/FantasyDataRefresh/Teams/{season}")
async def refresh_fd_teams(
    season: FantasyDataSeason,
    client: AsyncIOMotorClient = Depends(get_odm),
):
    # first we'll grab Kenpom CSV in this step, renaming a column
    kenpom_2020_df = pandas.read_csv(
        pathlib.Path(f"src/db/kenpom_{season}.csv"),
    ).rename(columns={"Team": "kenpom_team"})
    # mapping table of Kenpom names to FantasyData.io names
    school_names_df = pandas.read_csv(
        pathlib.Path(f"src/db/school_names.csv"),
    ).rename(columns={"Team": "kenpom_team"})
    # join kenpom data to map table
    kenpom_mapped_df = (
        school_names_df.merge(kenpom_2020_df, on="kenpom_team", how="inner")
        .rename(columns={"fd_team_id": "TeamID"})
        .set_index("TeamID")
    )

    # read fantasydata
    r = requests.get(
        "https://api.sportsdata.io/api/cbb/fantasy/json/Teams"
        + "?key="
        + FANTASY_DATA_KEY_CBB
    )

    # read teams table, set index
    teams_df = pandas.DataFrame(r.json()).set_index("TeamID")

    # drop columns we don't need, then teams with no conference
    teams_df.drop(
        columns=[
            "Active",
            "ApRank",
            "Wins",
            "Losses",
            "ConferenceWins",
            "ConferenceLosses",
        ],
        inplace=True,
    )
    teams_df.dropna(inplace=True)

    # merge kenpom and fd, then drop columns that were only needed for mapping
    teams_df = (
        teams_df.join(kenpom_mapped_df, how="inner")
        .drop(columns=["fd_key", "fd_school", "fd_name", "kenpom_team"])
        .convert_dtypes()
    )

    # season should be string (ex: 2020POST) so we can concat with TeamID
    teams_df["Season"] = teams_df["Season"].map(str).astype("string")
    teams_df["GlobalTeamID"] = teams_df["GlobalTeamID"].map(str).astype("string")
    teams_df["SeasonTeamID"] = teams_df["GlobalTeamID"] + teams_df["Season"]

    # back to json for writing to DB. reset index so TeamID makes it in
    engine = AIOEngine(motor_client=client, database="autobracket")
    p = orjson.loads(teams_df.to_json(orient="records"))
    await engine.save_all([CBBTeam(**doc) for doc in p])

    return {"message": "Mongo refresh complete!"}
