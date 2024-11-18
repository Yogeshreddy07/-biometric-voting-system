import sqlite3

# Connect to your database file
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Clear all data from the tables
cursor.execute("DELETE FROM voters")
cursor.execute("DELETE FROM candidates")
cursor.execute("DELETE FROM votes")

# Commit the changes and close the connection
conn.commit()
conn.close()

print("All records have been deleted from voters, candidates, and votes tables.")
