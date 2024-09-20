
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship  
from sqlalchemy.orm import sessionmaker
import concurrent.futures
from os import path
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

    images = relationship("Image", back_populates="listing")

    def __repr__(self):
        return '<Mls_homes {}>'.format(self.mls)

class Image(Base):
    __tablename__ = 'images'
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey('mls_homes.id'))
    urls = Column(String, index=True)
    listing = relationship("Mls_homes", back_populates="images")


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
        Base.metadata.drop_all(bind=homes_engine)
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
    
def process_row(row_data):
    try:
        mls, price, address, description, availability, bedrooms, bath, full, half, acres, age, sqft, fireplace, basement, garage, spaces, count, image_urls = row_data
        
        cost_formatted = f"${price:,.2f}"

        return {
            "MLS": mls,
            "COST": cost_formatted,
            "ADDRESS": address,
            "DESCRIPTION": description,
            "STATUS": availability,
            "BEDROOMS": bedrooms,
            "BATH": bath,
            "FULL": full,
            "HALF": half,
            "ACRES": acres,
            "AGE": age,
            "SQFT": sqft,
            "FIREPLACE": fireplace,
            "BASEMENT": basement,
            "GARAGE": garage,
            "SPACES": spaces,
            "COUNT": count,
            "URLS": image_urls,
        }
    except Exception as e:
        print(f"Error processing listing {mls}: {e}")
        return None

def get_homes_from_db():
    session = homes_sessionLocal2()
    try:
        listings = session.query(Mls_homes).all()

        if not listings:
            print("No listings found.")
            return []

        row_data = [
            (
                row.mls,
                row.price,
                row.address,
                row.description,
                row.availability,
                row.bedrooms,
                row.bath,
                row.full,
                row.half,
                row.acres,
                row.age,
                row.sqft,
                row.fireplace,
                row.basement,
                row.garage,
                row.spaces,
                row.count,
                [image.urls for image in row.images]
            )
            for row in listings
        ]

        with concurrent.futures.ProcessPoolExecutor() as executor:
            formatted_listings = list(executor.map(process_row, row_data))

        formatted_listings = [listing for listing in formatted_listings if listing is not None]

        return formatted_listings
    except Exception as e:
        print(f"An error occurred while retrieving listings: {e}")
        return []
    finally:
        session.close()



def view_images_from_db():
    import sqlite3
    conn = sqlite3.connect('brightscrape/brightmls_homes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM images")
    image_data = cursor.fetchall()
    for row in image_data:
        print(row)
    conn.close()
#view_images_from_db()

def add_images_from_folders(base_folder):
    Base.metadata.create_all(homes_engine2)
    db = homes_sessionLocal2()
    try:
        # Drop the images table if it exists and recreate it
        Image.__table__.drop(db.bind, checkfirst=True)
        Base.metadata.create_all(homes_engine2)

        # Query all listings from the database
        listings = db.query(Mls_homes).all()

        for listing in listings:
            mls = listing.mls
            # Construct the folder path based on MLS
            folder_path = os.path.join(base_folder, mls)

            # Check if the folder exists
            if os.path.isdir(folder_path):
                print(f"Found folder for MLS: {mls}")

                # List all image files in the folder
                for filename in os.listdir(folder_path):
                    if filename.endswith(('.jpg', '.jpeg', '.png', '.webp')):  # Supported image formats
                        # Save the relative path
                        relative_image_url = f'static/homes_images/{mls}/{filename}'

                        # Create a new Image instance
                        new_image = Image(listing_id=listing.id, urls=relative_image_url)

                        # Add the image to the session
                        db.add(new_image)

                # Commit after adding new images for the current listing
                db.commit()
                print(f"Added images for MLS: {mls}")

            else:
                print(f"No folder found for MLS: {mls}")

    except Exception as e:
        print(f"An error occurred while adding images: {e}")
        db.rollback()
    finally:
        db.close()

# Example usage
base_folder = 'start_files/static/homes_images/'


base_folder = 'start_files/static/homes_images/'
#add_images_from_folders(base_folder)
