from .const import Const
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine('sqlite:///{}'.format(Const.DB), convert_unicode=True)
session = scoped_session(sessionmaker(autocommit=False, autoflush=False,
                                      bind=engine))
Base = declarative_base()
Base.query = session.query_property()


def init_db():
    import data.models  # NOQA
    Base.metadata.create_all(bind=engine)
