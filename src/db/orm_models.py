from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

# https://docs.sqlalchemy.org/en/14/tutorial/metadata.html#defining-table-metadata-with-the-orm
Base = declarative_base()

class QuoteORM(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True)
    quote_text = Column(String)
    quote_origin = Column(String)

    def __repr__(self):
        return f"Quote(id={self.id}, quote_text={self.quote_text}, quote_origin={self.quote_origin}"
