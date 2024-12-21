import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
#from dotenv import load_dotenv

#load_dotenv()
Base = declarative_base()

database_url = os.environ.get("DATABASE_URL","mysql+pymysql://ThoshikaFS:Thoshika@FS456@127.0.0.1/tfs_python")
engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_database_session() -> Generator:
    try:
        data_base = SessionLocal()
        yield data_base
    finally:
        data_base.close()  # noqa
