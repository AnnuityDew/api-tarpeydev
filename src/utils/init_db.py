# begin database init code
metadata = sqlalchemy.MetaData()
quotes = sqlalchemy.Table(
    "quotes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("quote_text", sqlalchemy.String),
    sqlalchemy.Column("quote_origin", sqlalchemy.String),
)
metadata.create_all(engine_object.engine)