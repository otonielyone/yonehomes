from sqlalchemy import create_engine, Column, Integer, String, Float
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
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


DATABASE_URL = "sqlite:///brightscrape/brightmls.db"
homes_engine = create_engine(DATABASE_URL)
homes_sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=homes_engine)
Base = declarative_base()

class Mls_homes(Base):
    __tablename__ = 'mls_homes'
    mls = Column(String(20), primary_key=True, index=True)
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
    hash = Column(String(1000), index=True)

    def __repr__(self):
        return '<Mls_homes {}>'.format(self.mls)

class Mls_homes_temp(Base):
    __tablename__ = 'mls_homes_temp'
    mls = Column(String(20), primary_key=True, index=True)
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
    hash = Column(String(1000), index=True)

    def __repr__(self):
        return '<Mls_homes_temp {}>'.format(self.mls)

def init_homes_db():
    db_path = 'brightscrape/brightmls.db'
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    if not os.path.exists(db_path):
        print("Creating database file...")
        try:
            Base.metadata.drop_all(bind=homes_engine)
            Base.metadata.create_all(bind=homes_engine)
            print("Database and tables created successfully.")
        except SQLAlchemyError as e:
            print(f"An error occurred while creating the database: {e}")
    else:
        print("Database file already exists.")    


def check_and_create_original_homes_table(db):
    inspector = inspect(db.get_bind())
    if not inspector.has_table('mls_homes'):
        logger.info("Creating original Mls_homes table...")
        Base.metadata.create_all(bind=db.get_bind(), tables=[Mls_homes.__table__])
        logger.info("Original Mls_homes table created.")

def drop_and_create_temp_homes_table(db):
    Mls_homes_temp.__table__.drop(db.get_bind(), checkfirst=True)
    Base.metadata.create_all(bind=db.get_bind(), tables=[Mls_homes_temp.__table__])
    logger.info("Temporary Mls_homes_temp table created.")

def copy_homes_to_temp(db):
    original_listings = db.query(Mls_homes).all()
    logger.info(f"Found {len(original_listings)} records in the original table.")

    if original_listings:
        temp_listings = [
            Mls_homes_temp(
                mls=item.mls,
                address=item.address,
                price=item.price,
                description=item.description,
                availability=item.availability,
                bedrooms=item.bedrooms,
                bath=item.bath,
                full=item.full,
                half=item.half,
                acres=item.acres,
                age=item.age,
                sqft=item.sqft,
                fireplace=item.fireplace,
                basement=item.basement,
                garage=item.garage,
                spaces=item.spaces,
                count=item.count,
                hash=item.hash
            )
            for item in original_listings
        ]
        
        # Batch processing for bulk inserts
        batch_size = 100
        for i in range(0, len(temp_listings), batch_size):
            db.bulk_save_objects(temp_listings[i:i + batch_size])
        db.commit()
        logger.info(f"Copied {len(temp_listings)} records from original table to temporary table.")
    else:
        logger.warning("No records found in the original table.")

def init_homes_db_temp():
    try:
        with homes_sessionLocal() as db:
            logger.info("Reinitializing temporary database...")
            check_and_create_original_homes_table(db)
            drop_and_create_temp_homes_table(db)
            copy_homes_to_temp(db)
    except SQLAlchemyError as e:
        logger.error(f"An error occurred while initializing the temporary database: {e}")




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
        "HASH": row['hash'],
    }


def get_homes_from_db():
    db = None
    try:
        db = homes_sessionLocal()
        listings = db.query(Mls_homes).all()
        
        listings_dict = [listing.__dict__ for listing in listings]
        print(f"Listings: {listings_dict}") 
        df = pd.DataFrame(listings_dict)
   
        with ThreadPoolExecutor() as executor:
            formatted_listings = list(executor.map(process_row, df.to_dict(orient='records')))
        
        return formatted_listings
    except Exception:
        print(f"An error occurred while retrieving listings")
        return []
    finally:
        if db:
            db.close()



print(len(get_homes_from_db()))