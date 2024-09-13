
from sqlalchemy import create_engine, Column, Integer, String, Float
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from os import path
import pandas as pd
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


Base = declarative_base()

class Mls_rentals(Base):
    __tablename__ = 'mls'
    id = Column(Integer, primary_key=True, index=True)
    mls = Column(String(20), unique=True, index=True)
    address = Column(String(100), index=True)
    price = Column(Float, index=True)
    description = Column(String(1000), index=True)
    availability = Column(String(20), index=True)
    bedrooms = Column(String(5), index=True)
    bath = Column(String(5), index=True)
    #images = Column(Text)  # Store base64 encoded image strings as comma-separated text
        
    def __repr__(self):
        return '<User {}>'.format(self.mls)

# Setup SQLAlchemy engine and session
DATABASE_URL = "sqlite:///brightscrape/_rentals_pending.db?timeout=300"
rentals_engine = create_engine(DATABASE_URL)
rentals_sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rentals_engine)

DATABASE_URL2 = "sqlite:///brightscrape/brightmls_rentals.db"
rentals_engine2 = create_engine(DATABASE_URL2)
rentals_sessionLocal2 = sessionmaker(autocommit=False, autoflush=False, bind=rentals_engine2)

def init_rentals_db():
    db_path = 'brightscrape/_rentals_pending.db'
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    if not path.exists(db_path):
        print("Creating database file...")
        Base.metadata.create_all(bind=rentals_engine)
    else:
        print("Database file already exists.")


def init_rentals2_db():
    db_path = 'brightscrape/brightmls_rentals.db'
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)



def replace_old_db():
    # Define the URLs for the old and new databases
    old_db_path = "brightscrape/_rentals_pending.db"
    new_db_path = "brightscrape/brightmls_rentals.db"
    
    if os.path.exists(old_db_path):
        try:
            os.rename(old_db_path, new_db_path)
            print(f"Database renamed from {old_db_path} to {new_db_path}")
        except Exception:
            print(f"Error renaming database")
    

def process_row(row):
    cost_formatted = f"${row['price']:,.2f}"
    
    mls_directory = f'/var/www/html/fastapi_project/start_files/static/images/{row["mls"]}'

    image_list = []
    if os.path.exists(mls_directory):
        for filename in os.listdir(mls_directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                image_path = os.path.join(mls_directory, filename)
                image_list.append(image_path)
    
    return {
        "MLS": row['mls'],
        "COST": cost_formatted,
        "ADDRESS": row['address'],
        "DESCRIPTION": row['description'],
        "STATUS": row['availability'],
        "BEDROOMS": row['bedrooms'],
        "BATH": row['bath']
    }


def get_rentals_from_db():
    try:
        db = rentals_sessionLocal2()
        listings = db.query(Mls_rentals).all()
        listings_dict = [listing.__dict__ for listing in listings]
        df = pd.DataFrame(listings_dict)
        
        # Check if required columns are present
        required_columns = {'mls', 'price', 'address', 'description', 'availability', 'bedrooms', 'bath'}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise KeyError(f"Missing columns: {', '.join(missing_columns)}")
        
        with ThreadPoolExecutor() as executor:
            formatted_listings = list(executor.map(process_row, df.to_dict(orient='records')))
        
        return formatted_listings
    except Exception:
        print(f"An error occurred while retrieving listings")
        return [] 
    finally:
        if db:
            db.close()

