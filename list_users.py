import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute("SELECT username, role FROM users")
users = cursor.fetchall()

for user in users:
    print(f"Username: {user[0]}, Role: {user[1]}")

conn.close()
