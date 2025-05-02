import pyodbc


def connect_db():
    """
    Standardized database connection function used across the application.
    Returns a database connection object or None if connection fails.
    """
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=localhost;"
            "DATABASE=Capstones;"
            "Trusted_Connection=yes;"
        )
        return conn
    except pyodbc.Error as e:
        print("Database connection failed:", e)
        return None


# Test the connection when this module is run directly
if __name__ == "__main__":
    conn = connect_db()
    if conn:
        print("Database connection successful!")
        conn.close()
    else:
        print("Failed to connect to database.")
