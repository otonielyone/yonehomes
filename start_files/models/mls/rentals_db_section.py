
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy import create_engine, Column, Integer, String, Float
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.exc import SQLAlchemyError
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
    __tablename__ = 'mls_rentals'
    id = Column(Integer, primary_key=True, index=True)
    mls = Column(String(20), unique=True, index=True)
    address = Column(String(100), index=True)
    price = Column(Float, index=True)
    description = Column(String(1000), index=True)
    availability = Column(String(20), index=True)
    bedrooms = Column(String(5), index=True)
    bath = Column(String(5), index=True)
    count = Column(Integer, index=True)
    
    def __repr__(self):
        return '<Mls_rentals {}>'.format(self.mls)

# Setup SQLAlchemy engine and session
DATABASE_URL = "sqlite:///brightscrape/_rentals_pending.db?timeout=300"
rentals_engine = create_engine(DATABASE_URL)
rentals_sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rentals_engine)

DATABASE_URL2 = "sqlite:///brightscrape/brightmls_rentals.db?timeout=300"
rentals_engine2 = create_engine(DATABASE_URL2)
rentals_sessionLocal2 = sessionmaker(autocommit=False, autoflush=False, bind=rentals_engine2)

def init_rentals_db():
    db_path = 'brightscrape/_rentals_pending.db'
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    if not os.path.exists(db_path):
        print("Creating database file...")
        try:
            Base.metadata.drop_all(bind=rentals_engine)
            Base.metadata.create_all(bind=rentals_engine)
            print("Database and tables created successfully.")
        except SQLAlchemyError as e:
            print(f"An error occurred while creating the database: {e}")
    else:
        print("Database file already exists.")    

def init_rentals2_db():
    db_path = 'brightscrape/brightmls_rentals.db'
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)

def replace_old_rentals_db():
    old_db_path = "brightscrape/_rentals_pending.db"
    new_db_path = "brightscrape/brightmls_rentals.db"
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
        "COUNT": row['count'],
    }


def get_rentals_from_db():
    db = None
    try:
        db = rentals_sessionLocal2()
        listings = db.query(Mls_rentals).all()
        
        listings_dict = [listing.__dict__ for listing in listings]
        print(f"Listings: {listings_dict}")  # Debugging line
        df = pd.DataFrame(listings_dict)
        
        required_columns = {'mls', 'price', 'address', 'description', 'availability', 'bedrooms', 'bath', 'count'}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise KeyError(f"Missing columns: {', '.join(missing_columns)}")
        
        with ThreadPoolExecutor() as executor:
            formatted_listings = list(executor.map(process_row, df.to_dict(orient='records')))
        
        return formatted_listings
    except Exception as e:
        print(f"An error occurred while retrieving listings: {e}")
        return [] 
    finally:
        if db:
            db.close()





