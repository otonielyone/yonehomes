import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Define the database path
DATABASE_URL = "sqlite:///brightscrape/brightmls.db?timeout=300"

# Setup SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    user_id = Column(Integer, primary_key=True, index=True)
    mls = Column(String(20), unique=True, index=True)
    address = Column(String(100), index=True)
    price = Column(Float, index=True)
    description = Column(String(1000), index=True)
    availability = Column(String(20), index=True)
    images = Column(Text, index=False)  
    
    def __repr__(self):
        return '<User {}>'.format(self.mls)

    @property
    def image_list(self):
        return json.loads(self.images) if self.images else []

    @image_list.setter
    def image_list(self, value):
        self.images = json.dumps(value)

def init_db():
    db_path = 'brightscrape/brightmls.db'  
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    if not os.path.exists(db_path):
        print("Creating database file...")
        Base.metadata.create_all(bind=engine)
    else:
        print("Database file already exists.")

def get_users_from_db(db: Session):
    users = db.query(User).all()
    return [
        {
            "MLS": user.mls,
            "COST": f"${user.price:,.2f}",
            "ADDRESS": user.address,
            "DESCRIPTION": user.description,
            "STATUS": user.availability,
            "PHOTOS": user.image_list
        }
        for user in users
    ]

# Initialize the database (if not already created)
init_db()

# Create a new session
db = SessionLocal()

# Fetch and print users
users_data = get_users_from_db(db)
print(users_data[0][1])
