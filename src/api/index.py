# import Python packages
import random
from typing import List

# import third party packages
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.future import Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

# import custom local stuff
from src.api.security import validate_jwt
from src.db.alchemy import get_alchemy
from src.db.models import QuoteORM, Quote, QuotePatch


index_api = APIRouter(
    prefix="",
    tags=["meta"],
    dependencies=[Depends(validate_jwt)],
)


@index_api.get('/quote/random', response_model=Quote)
async def random_quote(engine: Engine = Depends(get_alchemy)):
    """Chooses a random quote from the database to show on the frontpage.

    Currently, this queries the entire table from the database before performing
    a random selection. We should probably cache the number of quotes in the table
    and then randomly select based on id.

    """
    with Session(engine) as session:
        sql = select(QuoteORM)
        result = session.execute(sql).scalars().all()
    
    if result:
        return random.choice(result)
    else:
        raise HTTPException(status_code=404, detail="No data found!")


@index_api.get('/quote/all', response_model=List[Quote])
async def get_all_quotes(engine: Engine = Depends(get_alchemy)):
    with Session(engine) as session:
        sql = select(QuoteORM)
        result = session.execute(sql).scalars().all()
    
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="No data found!")


@index_api.post('/quote')
async def add_quotes(
    row_list: List[Quote],
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        for row in row_list:
            # conversion from Pydantic model to ORM model
            session.add(QuoteORM(**row.dict()))
        session.commit()

    return {
        "result": row_list,
    }


@index_api.get('/quote/{id}', response_model=Quote)
async def get_quote(
    id: int,
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        sql = select(QuoteORM).where(QuoteORM.id == id)
        # one returns a Row object, which is a named tuple.
        # using scalar_one to access the object directly instead.
        try:
            result = session.execute(sql).scalar_one()
        except NoResultFound:
            raise HTTPException(status_code=404, detail="No data found!")

    return result


@index_api.patch('/quote/{id}')
async def edit_quote(
    id: int,
    patch: QuotePatch,
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        sql = select(QuoteORM).where(QuoteORM.id == id)
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

    return {
        "result": patch,
    }


@index_api.delete('/quote/{id}')
async def delete_quote(
    id: int,
    engine: Engine = Depends(get_alchemy),
):
    with Session(engine) as session:
        deletion = session.get(QuoteORM, id)
        if deletion is None:
            raise HTTPException(status_code=404, detail="No data found!")
        session.delete(deletion)
        session.commit()

    return {
        "result": deletion,
    }
