import sqlite3

# Membuat koneksi ke database (jika belum ada akan dibuat)
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Membuat tabel 'users' jika belum ada
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
''')

conn.commit()
conn.close()
print("Database dan tabel 'users' berhasil dibuat.")
