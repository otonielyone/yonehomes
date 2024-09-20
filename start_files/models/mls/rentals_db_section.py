
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship  
import concurrent.futures
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

    images = relationship("Image", back_populates="listing")

    def __repr__(self):
        return '<Mls_rentals {}>'.format(self.mls)

class Image(Base):
    __tablename__ = 'images'
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey('mls_rentals.id'))
    urls = Column(String, index=True)

    listing = relationship("Mls_rentals", back_populates="images")

    
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


def process_row(listing_data):
    try:
        mls, price, address, description, availability, bedrooms, bath, count, image_urls = listing_data
        
        cost_formatted = f"${price:,.2f}"

        return {
            "MLS": mls,
            "COST": cost_formatted,
            "ADDRESS": address,
            "DESCRIPTION": description,
            "STATUS": availability,
            "BEDROOMS": bedrooms,
            "BATH": bath,
            "COUNT": count,
            "URLS": image_urls,
        }
    except Exception as e:
        print(f"Error processing listing {mls}: {e}")
        return None

def get_rentals_from_db():
    session = rentals_sessionLocal2()
    try:
        listings = session.query(Mls_rentals).all()

        if not listings:
            print("No listings found.")
            return []

        listing_data = [
            (
                listing.mls,
                listing.price,
                listing.address,
                listing.description,
                listing.availability,
                listing.bedrooms,
                listing.bath,
                listing.count,
                [image.urls for image in listing.images]
            )
            for listing in listings
        ]

        with concurrent.futures.ProcessPoolExecutor() as executor:
            formatted_listings = list(executor.map(process_row, listing_data))

        formatted_listings = [listing for listing in formatted_listings if listing is not None]

        return formatted_listings
    except Exception as e:
        print(f"An error occurred while retrieving listings: {e}")
        return []
    finally:
        session.close()

def view_images_from_db():
    import sqlite3
    conn = sqlite3.connect('brightscrape/brightmls_rentals.db')
    cursor = conn.cursor()

    # Execute the query to fetch all images
    cursor.execute("SELECT * FROM images")

    # Fetch all results
    image_data = cursor.fetchall()

    # Print results
    for row in image_data:
        print(row)

    # Close the connection
    conn.close()
#view_images_from_db()


def add_images_from_folders(base_folder):
    # Drop the images table if it exists and recreate it
    Image.__table__.drop(rentals_engine2, checkfirst=True)
    Base.metadata.create_all(rentals_engine2)
    
    db = rentals_sessionLocal2()
    try:
        # Query all listings from the database
        listings = db.query(Mls_rentals).all()

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
                        relative_image_url = f'static/rentals_images/{mls}/{filename}'

                        # Create a new Image instance
                        new_image = Image(listing_id=listing.id, urls=relative_image_url)

                        # Add the image to the session
                        db.add(new_image)

                # Commit after adding images for the current listing
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
base_folder = 'start_files/static/rentals_images/'
#add_images_from_folders(base_folder)
