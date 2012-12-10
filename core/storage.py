import datetime as pydatetime
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker, relationship, validates
from sqlalchemy.ext.declarative import declarative_base
from dateutil.parser import parse as date_parse

ESTATE_WANTED = 'wanted'
ESTATE_SEARCHING = 'searching'
ESTATE_FETCHING = 'fetching'
ESTATE_PROCESSING = 'processing'
ESTATE_SKIPPED = 'skipped'
ESTATE_IGNORED = 'ignored'
ESTATE_EXCEPTION = 'exception'

EPISODE_STATES = (ESTATE_WANTED, ESTATE_SEARCHING, ESTATE_FETCHING, ESTATE_PROCESSING,
                  ESTATE_SKIPPED, ESTATE_IGNORED, ESTATE_EXCEPTION)
DEFAULT_STATE = ESTATE_IGNORED


Base = declarative_base()

class Series(Base):
    __tablename__ = 'series'

#    id = Column(Integer, primary_key=True, autoincrement=True)
    tvdb_id = Column(Integer, primary_key=True)
    imdb_id = Column(Integer)
    zap2it_id = Column(Integer)
    first_aired = Column(Date, nullable=False)
    airtime = Column(Time)
    airday = Column(String(10))
    network = Column(String(50))
    banner = Column(String(150))
    language = Column(String(2))
    name = Column(String(150))
    status = Column(String(50))
    overview = Column(Text, nullable=False)
    episodes = relationship("Episode", backref="series")

    @validates('airtime')
    def validate_airtime(self, key, value):
        if isinstance(value, pydatetime.time):
            return value
        return date_parse(value).time()

    @validates('first_aired')
    def validate_aired(self, key, value):
        if isinstance(value, pydatetime.datetime):
            return value
        return date_parse(value)


class Episode(Base):
    __tablename__ = 'episode'
    __table_args__ = (
        UniqueConstraint('series_id', 'season', 'episode'),
    )

    id = Column(Integer, primary_key=True, autoincrement=False)
    series_id = Column(Integer, ForeignKey('series.tvdb_id'))
    season = Column(Integer)
    episode = Column(Integer)
    air_date = Column(Date)
    name = Column(String(250))
    state = Column(String(50))

    @validates('air_date')
    def validate_airdate(self, key, value):
        if isinstance(value, pydatetime.date):
            return value
        return date_parse(value)

    @validates('state')
    def validate_state(self, key, value):
        if value not in EPISODE_STATES:
            raise ValueError('State must be one of: {}'.format(', '.join(EPISODE_STATES)))
        return value

    @classmethod
    def get_waiting(cls, session):
        today = pydatetime.datetime.today()
        return session.query(cls).filter(cls.air_date <= today).filter(cls.state == ESTATE_WANTED).all()

    def __unicode__(self):
        return '({e.id}) S{e.season:02d}E{e.episode:02d} - {e.name}'.format(e=self)


engine = None
def open_engine(connect_string):
    global engine
    engine = create_engine(connect_string)

def initialize_db():
    Base.metadata.create_all(engine)

def get_session():
    Session = sessionmaker(bind=engine)
    return Session()
