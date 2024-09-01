import os
import sqlite3
import pandas as pd




db_path = 'brightmls.db'
if not os.path.exists(db_path):
    print(f"Database file not found at {db_path}")
else:
    print("Database file exists.")


    
# Connect to the database
conn = sqlite3.connect('brightmls.db')

# Query to load data into a DataFrame
df = pd.read_sql_query("SELECT * FROM users", conn)

# Display the DataFrame
df.head()
