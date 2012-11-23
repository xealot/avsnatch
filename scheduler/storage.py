from sqlalchemy import *

metadata = MetaData()

engine = create_engine('sqlite:///:memory:')

show = Table('show', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('tvdb_id', Integer, index=True),
    Column('imdb_id', Integer),
    Column('zap2it_id', Integer),
    Column('first_aired', Date, nullable = False),
    Column('banner', String(150)),
    Column('language', String(2)),
    Column('name', String(150)),
    Column('overview', Text, nullable = False)
)

episode = Table('episode', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('show_id', Integer, ForeignKey('show.id')),
    Column('season', Integer),
    Column('episode', Integer),
    Column('air_date', Date),
    Column('name', String(250)),
    Column('state', String(50))
)

metadata.create_all(engine)
