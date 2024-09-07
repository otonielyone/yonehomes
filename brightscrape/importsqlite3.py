import base64
import pandas as pd
import sqlite3
import os
import pickle  # Use pickle if the list was serialized with it

# Path to your database file
db_path = 'brightscrape/brightmls.db'

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
def generate_html_divs(binary_data_list):
    html = ""
    for binary_data in binary_data_list:
        base64_str = binary_to_base64(binary_data)
        if base64_str:
            html += f'<div><img src="data:image/jpeg;base64,{base64_str}" alt="Image" style="width:100px;height:100px;"/></div>'
    return html

# Function to deserialize the image list if it is serialized
def deserialize_image_list(serialized_data):
    try:
        return pickle.loads(serialized_data)
    except (pickle.UnpicklingError, TypeError):
        return []

# Check if the database file exists
if not os.path.exists(db_path):
    print(f"Database file not found at {db_path}")
else:
    print("Database file exists.")

    # Connect to the database
    conn = sqlite3.connect(db_path)

    # Query to load data into a DataFrame
    df = pd.read_sql_query("SELECT * FROM user", conn)  # Ensure table name is correct

    # Close the database connection
    conn.close()

    # Check the first few rows of the DataFrame
    print(df.head())

    # Apply the deserialization and HTML generation functions to each row
    df['image_list_html'] = df['images'].apply(
        lambda x: generate_html_divs(deserialize_image_list(x)) if x else ""
    )

    # Print the DataFrame with the new column showing the HTML
    print(df[['mls', 'image_list_html']])

   
