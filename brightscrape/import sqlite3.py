import sqlite3
import pandas as pd
import os

db_path = '/var/www/html/fastapi_project/brightscrape/brightmls.db'

# Check if the database file exists
if not os.path.exists(db_path):
    print(f"Database file not found at {db_path}")
else:
    print("Database file exists.")

    # Connect to the database
    conn = sqlite3.connect(db_path)

    # Query to load data into a DataFrame
    df = pd.read_sql_query("SELECT * FROM user", conn)  # Ensure table name is correct

    # Display the DataFrame
    print(df)
