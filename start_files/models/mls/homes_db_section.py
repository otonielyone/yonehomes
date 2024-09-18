
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base
from concurrent.futures import ThreadPoolExecutor
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

class Mls_homes(Base):
    __tablename__ = 'mls_homes'
    id = Column(Integer, primary_key=True, index=True)
    mls = Column(String(20), unique=True, index=True)
    address = Column(String(100), index=True)
    price = Column(Float, index=True)
    description = Column(String(1000), index=True)
    availability = Column(String(20), index=True)
    bedrooms = Column(String(5), index=True)
    bath = Column(String(5), index=True)
    full = Column(String(5), index=True)
    half = Column(String(5), index=True)
    acres = Column(String(10), index=True)
    age = Column(String(5), index=True)
    sqft  = Column(String(5), index=True)
    fireplace = Column(String(5), index=True)
    basement = Column(String(5), index=True)
    garage = Column(String(5), index=True)
    spaces = Column(String(5), index=True)
    count = Column(String(5), index=True)

    def __repr__(self):
        return '<Mls_homes {}>'.format(self.mls)

DATABASE_URL = "sqlite:///brightscrape/_homes_pending.db?timeout=300"
homes_engine = create_engine(DATABASE_URL)
homes_sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=homes_engine)

DATABASE_URL2 = "sqlite:///brightscrape/brightmls_homes.db"
homes_engine2 = create_engine(DATABASE_URL2)
homes_sessionLocal2 = sessionmaker(autocommit=False, autoflush=False, bind=homes_engine2)

def init_homes_db():
    db_path = 'brightscrape/_homes_pending.db'
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    if not path.exists(db_path):
        print("Creating database file...")
        Base.metadata.create_all(bind=homes_engine)
    else:
        print("Database file already exists.")


def replace_old_homes_db():
    old_db_path = "brightscrape/_homes_pending.db"
    new_db_path = "brightscrape/brightmls_homes.db"
    new_db_backup_path = new_db_path + '.bak'
    
    if os.path.exists(new_db_backup_path):
        try:
            os.remove(new_db_backup_path)
            print(f"Removed old backup file {new_db_backup_path}")
        except Exception:
            print(f"Error removing backup file {new_db_backup_path}")
            return
    
    if os.path.exists(new_db_path):
        try:
            os.rename(new_db_path, new_db_backup_path)
            print(f"Renamed {new_db_path} to {new_db_backup_path}")
        except Exception:
            print(f"Error renaming new database to {new_db_backup_path}")
            return
    
    if os.path.exists(old_db_path):
        try:
            os.rename(old_db_path, new_db_path)
            print(f"Renamed {old_db_path} to {new_db_path}")
        except Exception:
            print(f"Error renaming old database to {new_db_path}")
    else:
        print(f"Old database {old_db_path} does not exist")
    
def process_row(row):
    cost_formatted = f"${row['price']:,.2f}"

    return {
        "MLS": row['mls'],
        "COST": cost_formatted,
        "ADDRESS": row['address'],
        "DESCRIPTION": row['description'],
        "STATUS": row['availability'],
        "BEDROOMS": row['bedrooms'],
        "BATH": row['bath'],
        "FULL": row['full'],
        "HALF": row['half'],
        "ACRES": row['acres'], 
        "AGE": row['age'],
        "SQFT": row['sqft'],
        "FIREPLACE": row['fireplace'],
        "BASEMENT": row['basement'], 
        "GARAGE": row['garage'],
        "SPACES": row['spaces'],
        "COUNT": row['count'],
    }


def get_homes_from_db():
    db = None
    try:
        db = homes_sessionLocal2()
        listings = db.query(Mls_homes).all()
        
        listings_dict = [listing.__dict__ for listing in listings]
        print(f"Listings: {listings_dict}")  # Debugging line
        df = pd.DataFrame(listings_dict)

        required_columns = {'mls', 'price', 'address', 'description', 'availability', 'bedrooms', 'bath', 'full', 'half', 'acres', 'age', 'sqft', 'fireplace', 'basement', 'garage', 'spaces', 'count'}
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