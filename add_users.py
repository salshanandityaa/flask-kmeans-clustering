import sqlite3
import bcrypt

def add_user(username, password, role):
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, hashed_password, role))
    conn.commit()
    conn.close()
    print(f"Pengguna '{username}' dengan peran '{role}' berhasil ditambahkan.")

if __name__ == '__main__':
    # Menambahkan pengguna admin dengan password 'admin123'
    add_user('admin', 'admin123', 'admin')
    # Menambahkan pengguna biasa dengan password 'user123'
    add_user('user', 'user123', 'user')