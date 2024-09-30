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
rentals_engine = create_engine(DATABASE_URL)
rentals_sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rentals_engine)
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
    hash = Column(String(1000), index=True)

    def __repr__(self):
        return '<Mls_rentals {}>'.format(self.mls)


class Mls_rentals_temp(Base):
    __tablename__ = 'mls_rentals_temp'
    id = Column(Integer, primary_key=True, index=True)
    mls = Column(String(20), unique=True, index=True)
    address = Column(String(100), index=True)
    price = Column(Float, index=True)
    description = Column(String(1000), index=True)
    availability = Column(String(20), index=True)
    bedrooms = Column(String(5), index=True)
    bath = Column(String(5), index=True)
    count = Column(Integer, index=True)
    hash = Column(String(1000), index=True)

    def __repr__(self):
        return '<Mls_rentals {}>'.format(self.mls)


def init_rentals_db():
    db_path = 'brightscrape/brightmls.db'
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


def init_rentals_db_temp():
    try:
        with rentals_sessionLocal() as db:
            logger.info("Reinitializing temporary database...")
            inspector = inspect(db.get_bind())
            if not inspector.has_table('mls_rentals'):
                logger.info("Original Mls_rentals table does not exist. Creating it...")
                Base.metadata.create_all(bind=db.get_bind(), tables=[Mls_rentals.__table__])
                logger.info("Original Mls_rentals table created.")
                
            Mls_rentals_temp.__table__.drop(db.get_bind(), checkfirst=True)
            Base.metadata.create_all(bind=db.get_bind(), tables=[Mls_rentals_temp.__table__])
            original_listings = db.query(Mls_rentals).all()
            if original_listings:
                temp_listings = [
                    Mls_rentals_temp(
                        mls=item.mls,
                        address=item.address,
                        price=item.price,
                        description=item.description,
                        availability=item.availability,
                        bedrooms=item.bedrooms,
                        bath=item.bath,
                        count=item.count,
                        hash=item.hash)
                    for item in original_listings]
                if temp_listings: 
                    db.bulk_save_objects(temp_listings)
                    db.commit()
                    logger.info(f"Copied {len(temp_listings)} records from original table to temporary table.")
                else:
                    logger.warning("No records found to copy to the temporary table.")
            else:
                logger.warning("No records found in the original table.")
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
        "COUNT": row['count'],
        "HASH": row['hash'],
    }


def get_rentals_from_db():
    DATABASE_URL = "sqlite:///brightscrape/brightmls.db"
    rentals_engine = create_engine(DATABASE_URL)
    rentals_sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rentals_engine)


    db = None
    try:
        db = rentals_sessionLocal()
        listings = db.query(Mls_rentals).all()
        
        listings_dict = [listing.__dict__ for listing in listings]
        print(f"Listings: {listings_dict}")
        df = pd.DataFrame(listings_dict)
        
        required_columns = {'mls', 'price', 'address', 'description', 'availability', 'bedrooms', 'bath', 'count', 'hash'}
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





