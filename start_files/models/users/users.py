from os import path
import os
from sqlalchemy import Text, create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.mutable import Mutable
import json

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    user_id = Column(Integer, primary_key=True, index=True)
    mls = Column(String(20), unique=True, index=True)
    address = Column(String(100), unique=True, index=True)
    price = Column(Float, index=True)
    description = Column(String(1000), index=True)
    availability = Column(String(20), index=True)
    images = Column(Text, index=False)  # Change from String to Text
    
    def __repr__(self):
        return '<User {}>'.format(self.mls)

    @property
    def image_list(self):
        return json.loads(self.images) if self.images else []

    @image_list.setter
    def image_list(self, value):
        self.images = json.dumps(value)

# Setup SQLAlchemy engine and session
DATABASE_URL = "sqlite:///brightscrape/brightmls.db" 
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    db_path = 'brightscrape/brightmls.db'  
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    if not path.exists(db_path):
        print("Creating database file...")
        Base.metadata.create_all(bind=engine)
    else:
        print("Database file already exists.")

