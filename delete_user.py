import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute("DELETE FROM users WHERE username = 'admin'")
conn.commit()
conn.close()

print("User 'admin' berhasil dihapus.")

import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute("DELETE FROM users WHERE username = 'user'")
conn.commit()
conn.close()

print("User 'user' berhasil dihapus.")