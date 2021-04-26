import csv
from pathlib import Path
import sqlalchemy
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.orm import declarative_base, Session

db_folder_path = Path('src/db')
db_file_path = db_folder_path / 'db.sqlite'
db_backup_path = db_folder_path / 'mongo_backup'

# https://docs.sqlalchemy.org/en/14/tutorial/metadata.html#defining-table-metadata-with-the-orm
Base = declarative_base()

class QuoteORM(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True)
    quote_text = Column(String)
    quote_origin = Column(String)

    def __repr__(self):
        return f"Quote(id={self.id}, quote_text={self.quote_text}, quote_origin={self.quote_origin}"


def sqlite_init_from_mongo():
    engine = sqlalchemy.create_engine(f"sqlite+pysqlite:///{db_file_path}", echo=True, future=True)

    # creates tables based on class definitions
    Base.metadata.create_all(engine)

    with Session(engine) as session, open(db_backup_path / 'quotes_quote.csv') as csv_file:
        csv_reader = csv.reader(csv_file)
        # headers first
        headers = next(csv_reader, None)
        # now loop over data
        for row in csv_reader:
            quote_dict = dict(zip(headers[2:], row[2:]))
            current_quote = QuoteORM(**quote_dict)
            print(current_quote)
            session.add(current_quote)
        
        # commit data to db
        session.commit()

        # select it all back out for viewing
        sql = select(QuoteORM)
        result = session.execute(sql).scalars().all()
        print(result)


if __name__ == "__main__":
    sqlite_init_from_mongo()
