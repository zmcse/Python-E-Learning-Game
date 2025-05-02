import pyodbc
from database_conn import connect_db

current_lecturer_id = None


def set_user(lecturer_id):
    global current_lecturer_id
    current_lecturer_id = lecturer_id


def get_user():
    return current_lecturer_id


def get_user_details():
    global current_lecturer_id
    print(f"Current lecturer ID: {current_lecturer_id}")  # Debug print
    
    if not current_lecturer_id:
        print("No lecturer ID set!")  # Debug print
        return None

    try:
        conn = connect_db()
        if not conn:
            print("Failed to connect to database!")  # Debug print
            return None

        cursor = conn.cursor()
        cursor.execute("Select LecturerID, Name, Email from Lecturers where LecturerID=?", (current_lecturer_id,))
        user = cursor.fetchone()
        conn.close()

        if user:
            print(f"Found user: {user}")  # Debug print
            return {"LecturerID": user[0], "Name": user[1], "Email": user[2]}
        else:
            print("No user found in database!")  # Debug print
            return None

    except Exception as e:
        print(f"Error in get_user_details: {e}")  # Debug print
        return None
    
    