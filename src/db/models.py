from typing import Optional, List, Dict
from enum import Enum, IntEnum
from datetime import date

from sqlalchemy import types
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, Date, Float, JSON
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel, Field

# https://docs.sqlalchemy.org/en/14/tutorial/metadata.html#defining-table-metadata-with-the-orm
Base = declarative_base()


class QuoteORM(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True)
    quote_text = Column(String)
    quote_origin = Column(String)

    def __repr__(self):
        return f"Quote(id={self.id}, quote_text={self.quote_text}, quote_origin={self.quote_origin})"


class Quote(BaseModel):
    quote_text: str
    quote_origin: str

    # necessary for parsing a SQLAlchemy ORM result
    class Config:
        orm_mode = True


class QuotePatch(BaseModel):
    quote_text: Optional[str]
    quote_origin: Optional[str]

    # necessary for parsing a SQLAlchemy ORM result
    class Config:
        orm_mode = True


class GameStatus(str, Enum):
    NOT_STARTED = "Not Started"
    STARTED = "Started"
    BEATEN = "Beaten"
    COMPLETED = "Completed"
    MASTERED = "Mastered"
    INFINITE = "Infinite"
    WISH_LIST = "Wish List"


class BacklogGameORM(Base):
    __tablename__ = "backlog_games"

    id = Column(Integer, primary_key=True)
    game_title = Column(String)
    sub_title = Column(String)
    game_system = Column(String)
    genre = Column(String)
    dlc = Column(Boolean)
    now_playing = Column(Boolean)
    game_status = Column(types.Enum(GameStatus))
    game_hours = Column(Integer)
    game_minutes = Column(Integer)
    actual_playtime = Column(Boolean)
    add_date = Column(Date)
    start_date = Column(Date)
    beat_date = Column(Date)
    complete_date = Column(Date)
    game_notes = Column(String)

    def __repr__(self):
        return f"BacklogGame(id={self.id}, game_title={self.game_title})"


class BacklogGame(BaseModel):
    game_title: str
    sub_title: Optional[str]
    game_system: str
    genre: str
    dlc: bool
    now_playing: bool
    game_status: GameStatus
    game_hours: Optional[int]
    game_minutes: Optional[int]
    actual_playtime: bool
    add_date: Optional[date]
    start_date: Optional[date]
    beat_date: Optional[date]
    complete_date: Optional[date]
    game_notes: Optional[str]

    # necessary for parsing a SQLAlchemy ORM result
    class Config:
        orm_mode = True


class Against(str, Enum):
    AGAINST = "against"
    FOR = "for"


class NickName(str, Enum):
    TARPEY = "Tarpey"
    CHRISTIAN = "Christian"
    NEEL = "Neel"
    BRANDO = "Brando"
    DEBBIE = "Debbie"
    DANNY = "Danny"
    MILDRED = "Mildred"
    HARDY = "Hardy"
    TOMMY = "Tommy"
    BRYANT = "Bryant"
    KINDY = "Kindy"
    SENDZIK = "Sendzik"
    SAMIK = "Samik"
    STEPHANIE = "Stephanie"
    DEBSKI = "Debski"
    BEN = "Ben"
    ARTHUR = "Arthur"
    CONTI = "Conti"
    FONTI = "Fonti"
    FRANK = "Frank"
    MIKE = "mballen"
    PATRICK = "Patrick"
    CHARLES = "Charles"
    JAKE = "Jake"
    BRAD = "Brad"
    BYE = "Bye"


class MLSeason(IntEnum):
    SEASON1 = 2013
    SEASON2 = 2014
    SEASON3 = 2015
    SEASON4 = 2016
    SEASON5 = 2017
    SEASON6 = 2018
    SEASON7 = 2019
    SEASON8 = 2020


class MLPlayoff(IntEnum):
    REGULAR = 0
    PLAYOFF = 1
    LOSERS = 2


class MLGameORM(Base):
    __tablename__ = "ml_games"

    id = Column(Integer, primary_key=True)
    away = Column(String)
    away_nick = Column(types.Enum(NickName))
    away_score = Column(Float)
    home = Column(String)
    home_nick = Column(types.Enum(NickName))
    home_score = Column(Float)
    week_start = Column(Integer)
    week_end = Column(Integer)
    season = Column(types.Enum(MLSeason))
    playoff = Column(types.Enum(MLPlayoff))

    def __repr__(self):
        return (
            f"MLGame(id={self.id}, away_nick={self.away_nick}, away_score={self.away_score}, "
            + f"home_nick={self.home_nick}, home_score={self.home_score})"
        )


class MLGame(BaseModel):
    away: str
    away_nick: NickName
    away_score: float
    home: str
    home_nick: NickName
    home_score: float
    week_start: int
    week_end: int
    season: MLSeason
    playoff: MLPlayoff


class MLGamePatch(BaseModel):
    away: Optional[str]
    away_nick: Optional[NickName]
    away_score: Optional[float]
    home: Optional[str]
    home_nick: Optional[NickName]
    home_score: Optional[float]
    week_start: Optional[int]
    week_end: Optional[int]
    season: Optional[MLSeason]
    playoff: Optional[MLPlayoff]


class MLTeamORM(Base):
    __tablename__ = "ml_teams"

    id = Column(Integer, primary_key=True)
    division = Column(String)
    full_name = Column(String)
    nick_name = Column(types.Enum(NickName))
    season = Column(types.Enum(MLSeason))
    playoff_rank = Column(Integer)
    active = Column(Boolean)

    def __repr__(self):
        return f"MLGame(id={self.id}, nick_name={self.nick_name}, season={self.season})"


class MLTeam(BaseModel):
    division: str
    full_name: str
    nick_name: NickName
    season: MLSeason
    playoff_rank: int
    active: bool


class MLTeamPatch(BaseModel):
    division: Optional[str]
    full_name: Optional[str]
    nick_name: Optional[NickName]
    season: Optional[MLSeason]
    playoff_rank: Optional[int]
    active: Optional[bool]


class MLNoteORM(Base):
    __tablename__ = "ml_notes"

    id = Column(Integer, primary_key=True)
    season = Column(types.Enum(MLSeason))
    note = Column(String)

    def __repr__(self):
        return f"MLGame(id={self.id}, season={self.season}, note={self.note})"


class MLNote(BaseModel):
    season: MLSeason
    note: str


class MLNotePatch(BaseModel):
    season: Optional[MLSeason]
    note: Optional[str]


class MLTableTransform(BaseModel):
    season: MLSeason
    playoff: MLPlayoff
    columns: List
    data: List


class MLBoxplotTransform(BaseModel):
    season: MLSeason
    for_data: Dict
    against_data: Dict


class CBBTeamORM(Base):
    __tablename__ = "cbb_teams"

    SeasonTeamID = Column(BigInteger, primary_key=True)
    Key = Column(String)
    School = Column(String)
    Name = Column(String)
    GlobalTeamID = Column(Integer)
    Conference = Column(String)
    TeamLogoUrl = Column(String)
    ShortDisplayName = Column(String)
    Stadium = Column(JSON)
    Season = Column(String)
    Rk = Column(Integer)
    Conf = Column(String)
    W = Column(Integer)
    L = Column(Integer)
    AdjEM = Column(Float)
    AdjO = Column(Float)
    AdjD = Column(Float)
    AdjT = Column(Float)
    Luck = Column(Float)
    OppAdjEM = Column(Float)
    OppO = Column(Float)
    OppD = Column(Float)
    NCAdjEM = Column(Float)

    def __repr__(self):
        return f"CBBTeam(SeasonTeamID={self.SeasonTeamID})"


class CBBTeam(BaseModel):
    SeasonTeamID: int = Field(primary_field=True)
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


class PlayerSeasonORM(Base):
    __tablename__ = "cbb_player_seasons"

    StatID = Column(Integer, primary_key=True)
    TeamID = Column(Integer)
    PlayerID = Column(Integer)
    SeasonType = Column(Integer)
    Season = Column(String)
    Name = Column(String)
    Team = Column(String)
    Position = Column(String)
    Games = Column(Integer)
    FantasyPoints = Column(Float)
    Minutes = Column(Integer)
    FieldGoalsMade = Column(Integer)
    FieldGoalsAttempted = Column(Integer)
    FieldGoalsPercentage = Column(Float)
    TwoPointersMade = Column(Integer)
    TwoPointersAttempted = Column(Integer)
    TwoPointersPercentage = Column(Float)
    ThreePointersMade = Column(Integer)
    ThreePointersAttempted = Column(Integer)
    ThreePointersPercentage = Column(Float)
    FreeThrowsMade = Column(Integer)
    FreeThrowsAttempted = Column(Integer)
    FreeThrowsPercentage = Column(Float)
    OffensiveRebounds = Column(Integer)
    DefensiveRebounds = Column(Integer)
    Rebounds = Column(Integer)
    Assists = Column(Integer)
    Steals = Column(Integer)
    BlockedShots = Column(Integer)
    Turnovers = Column(Integer)
    PersonalFouls = Column(Integer)
    Points = Column(Integer)
    FantasyPointsFanDuel = Column(Float)
    FantasyPointsDraftKings = Column(Float)
    two_attempt_chance = Column(Float)
    two_chance = Column(Float)
    three_chance = Column(Float)
    ft_chance = Column(Float)


class PlayerSeason(BaseModel):
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
    TwoPointersPercentage: float
    ThreePointersMade: int
    ThreePointersAttempted: int
    ThreePointersPercentage: float
    FreeThrowsMade: int
    FreeThrowsAttempted: int
    FreeThrowsPercentage: float
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


class SimulationDistORM(Base):
    __tablename__ = "cbb_simulation_distributions"

    id = Column(Integer, primary_key=True)
    away_key = Column(String)
    home_key = Column(String)
    season = Column(String)
    home_win_chance_max = Column(Float)
    max_margin_top = Column(Integer)
    max_margin_bottom = Column(Integer)
    home_win_chance_medium = Column(Float)
    medium_margin_top = Column(Integer)
    medium_margin_bottom = Column(Integer)
    home_win_chance_mild = Column(Float)
    mild_margin_top = Column(Integer)
    mild_margin_bottom = Column(Integer)
    home_win_chance_median = Column(Float)
    median_margin_top = Column(Integer)
    median_margin_bottom = Column(Integer)
    median_margin = Column(Integer)


class SimulationDist(BaseModel):
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
    median_margin: int


class FantasyDataSeason(str, Enum):
    PRIORSEASON1 = "2020"
    CURRENTSEASON = "2021"


class BracketFlavor(str, Enum):
    NONE = "none"
    MILD = "mild"
    MEDIUM = "medium"
    MAX = "max"


class SimulationRunORM(Base):
    __tablename__ = "cbb_simulation_runs"

    id = Column(Integer, primary_key=True)
    game_summary = Column(JSON)
    team_box_score = Column(JSON)
    full_box_score = Column(JSON)


class SimulationRun(BaseModel):
    game_summary: Dict
    team_box_score: Dict
    full_box_score: Dict


class SimulatedBracketORM(Base):
    __tablename__ = "cbb_simulated_brackets"

    id = Column(Integer, primary_key=True)
    bracket = Column(JSON)
    flavor = Column(types.Enum(BracketFlavor))


class SimulatedBracket(BaseModel):
    flavor: BracketFlavor
    bracket: Dict
