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



# Function to convert binary data to a Base64-encoded string
def binary_to_base64(binary_data):
    if binary_data:
        try:
            return base64.b64encode(binary_data).decode('utf-8')
        except Exception as e:
            print(f"Error encoding binary data: {e}")
            return None
    return None



# Function to generate HTML <div> elements for each image
def generate_image_src(binary_data_list):
    src_list = []
    for binary_data in binary_data_list:
        base64_str = binary_to_base64(binary_data)
        if base64_str:
            src_list.append(f'data:image/jpeg;base64,{base64_str}')
    return src_list

# Function to deserialize the image list if it is serialized
def deserialize_image_list(serialized_data):
    try:
        return pickle.loads(serialized_data)
    except (pickle.UnpicklingError, TypeError):
        return []

def get_listings_from_db(db):
    try:
        # Query the database for all listings
        listings = db.query(User).all()
        
        # Convert each User instance to a dictionary
        listings_dict = [user.__dict__ for user in listings]


        # Create a DataFrame from the list of dictionaries
        df = pd.DataFrame(listings_dict)

        # Ensure the 'images' column exists in the DataFrame
        if 'images' not in df.columns:
            raise KeyError("The 'images' column is missing from the DataFrame.")

        # Apply the deserialization and HTML generation functions to each row
        df['image_list_html'] = df['images'].apply(
            lambda x: generate_image_src(deserialize_image_list(x)) if x else ""
        )

        # Print the DataFrame with the new column showing the HTML
        print(df[['mls', 'image_list_html']])

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
