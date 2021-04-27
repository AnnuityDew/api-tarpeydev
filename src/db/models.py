from typing import Optional
from enum import Enum
from datetime import date

from sqlalchemy import types
from sqlalchemy import Column, Integer, String, Boolean, Date
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel

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
