# import Python packages
from typing import List, Optional

# import third party packages
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.future import Engine
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from odmantic import AIOEngine, Model, ObjectId

# import custom local stuff
from src.db.alchemy import get_sqlite
from src.db.motor import get_odm
from src.api.security import validate_jwt
from src.db.orm_models import QuoteORM


index_api = APIRouter(
    prefix="",
    tags=["meta"],
    dependencies=[Depends(validate_jwt)],
)


class Quote(BaseModel):
    id: int
    quote_text: str
    quote_origin: str

    # necessary for parsing a SQLAlchemy ORM result
    class Config:
        orm_mode = True


class QuotePatch(BaseModel):
    id: int
    quote_text: Optional[str]
    quote_origin: Optional[str]

    # necessary for parsing a SQLAlchemy ORM result
    class Config:
        orm_mode = True


@index_api.get('/quote/random', response_model=Quote)
async def random_quote(client: AsyncIOMotorClient = Depends(get_odm)):
    engine = AIOEngine(motor_client=client, database="quotes")
    collection = engine.get_collection(Quote)
    # random sample
    quote = await collection.aggregate([ { '$sample': { 'size': 1 } } ]).to_list(length=1)
    # convert aggregation list to Quote class
    quote = Quote(
        quote_text=quote[0]['quote_text'],
        quote_origin=quote[0]['quote_origin'],
    )
    return quote


@index_api.get('/quote/all', response_model=List[Quote])
async def get_all_quotes(
    engine: Engine = Depends(get_sqlite),
):
    with Session(engine) as session:
        sql = select(QuoteORM)
        result = session.execute(sql).scalars().all()
    
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="No data found!")


@index_api.post('/quote')
async def add_quotes(
    doc_list: List[Quote],
    client: AsyncIOMotorClient = Depends(get_odm),
):
    engine = AIOEngine(motor_client=client, database="quotes")
    result = await engine.save_all(doc_list)
    return {
        "result": result,
    }


@index_api.get('/quote/{oid}', response_model=Quote)
async def get_quote(
    oid: ObjectId,
    client: AsyncIOMotorClient = Depends(get_odm),
):
    engine = AIOEngine(motor_client=client, database="quotes")
    quote = await engine.find_one(Quote, Quote.id == oid)
    if quote:
        return quote
    else:
        raise HTTPException(status_code=404, detail="No data found!")


@index_api.patch('/quote/{oid}')
async def edit_quote(
    oid: ObjectId,
    patch: QuotePatch,
    client: AsyncIOMotorClient = Depends(get_odm),
):
    engine = AIOEngine(motor_client=client, database="quotes")
    quote = await engine.find_one(Quote, Quote.id == oid)
    if quote is None:
        raise HTTPException(status_code=404, detail="No data found!")

    patch_dict = patch.dict(exclude_unset=True)
    for attr, value in patch_dict.items():
        setattr(quote, attr, value)
    result = await engine.save(quote)

    return {
        "result": result,
    }


@index_api.delete('/quote/{oid}')
async def delete_quote(
    oid: ObjectId,
    client: AsyncIOMotorClient = Depends(get_odm),
):
    engine = AIOEngine(motor_client=client, database="quotes")
    quote = await engine.find_one(Quote, Quote.id == oid)
    if quote is None:
        raise HTTPException(status_code=404, detail="No data found!")

    await engine.delete(quote)

    return {
        "quote": quote,
    }
