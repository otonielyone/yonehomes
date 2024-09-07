import base64
import pickle
import pandas as pd
from sqlalchemy import LargeBinary, create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from os import path
import os


Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    user_id = Column(Integer, primary_key=True, index=True)
    mls = Column(String(20), unique=True, index=True)
    address = Column(String(100), index=True)
    price = Column(Float, index=True)
    description = Column(String(1000), index=True)
    availability = Column(String(20), index=True)
    images = Column(LargeBinary)  # Store serialized binary data directly

    def __repr__(self):
        return '<User {}>'.format(self.mls)

# Setup SQLAlchemy engine and session
DATABASE_URL = "sqlite:///brightscrape/brightmls.db?timeout=300"
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


# Function to deserialize the image list if it is serialized
def deserialize_image_list(serialized_data):
    try:
        return pickle.loads(serialized_data)
    except (pickle.UnpicklingError, TypeError):
        return []


def get_listings_from_db(db):
    try:
        listings = db.query(User).all()
        listings_dict = [user.__dict__ for user in listings]
        df = pd.DataFrame(listings_dict)
        if 'images' not in df.columns:
            raise KeyError("The 'images' column is missing from the DataFrame.")

        df['image_list_html'] = df['images'].apply(
            lambda x: deserialize_image_list(x) if x else ""
        )
        formatted_listings = []
        for _, row in df.iterrows():
            # Format the price field as currency
            cost_formatted = f"${row['price']:,.2f}"
            formatted_listings.append({
                "MLS": row['mls'],
                "COST": cost_formatted,
                "ADDRESS": row['address'],
                "DESCRIPTION": row['description'],
                "STATUS": row['availability'],
                "PHOTOS": row['image_list_html']
            })
        return formatted_listings
    except Exception as e:
        print(f"An error occurred while retrieving listings: {e}")
        return []