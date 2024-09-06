from sqlalchemy import Text, create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from os import path
import json
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
    images = Column(Text, index=False)  
    
    def __repr__(self):
        return '<User {}>'.format(self.mls)

    @property
    def image_list(self):
        return json.loads(self.images) if self.images else []

    @image_list.setter
    def image_list(self, value):
        self.images = json.dumps(value)

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


#def get_listings_from_db(db):
#    users = db.query(User).all()
#    return [
#        {
#            "MLS": user.mls,
#            "COST": f"${user.price:,.2f}",
#            "ADDRESS": user.address,
#            "DESCRIPTION": user.description,
#            "STATUS": user.availability,
#            "PHOTOS": user.image_list
#        }
#        for user in users
#    ]


def get_listings_from_db(db):
    # Query the database for all listings
    listings = db.query(User).all()  # Assuming `User` is the model but refers to "listings"
    
    formatted_listings = []
    
    for listing in listings:
        # Format the COST field as a currency
        cost_formatted = f"${listing.price:,.2f}"
        
        # Handle the PHOTOS list (assuming it is a list of filenames)
        photos_list = listing.image_list if listing.image_list else []
        
        formatted_listings.append({
            "MLS": listing.mls,
            "COST": cost_formatted,
            "ADDRESS": listing.address,
            "DESCRIPTION": listing.description,
            "STATUS": listing.availability,
            "PHOTOS": photos_list
        })
    
    # Return the list of formatted listings
    return formatted_listings
