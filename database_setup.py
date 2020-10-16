from sqlalchemy import create_engine

from models import *

engine = create_engine("sqlite:///db.sqlite")

if __name__ == "__main__":
    Base.metadata.create_all(engine)
