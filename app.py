from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import sqlite3
import os
from werkzeug.utils import secure_filename
import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['SECRET_KEY'] = 'kunci_rahasia_yang_sangat_kuat_dan_unik_anda_harus_mengubah_ini' # GANTI DENGAN STRING ACAK YANG KUAT UNATUK PRODUKSI!


def allowed_file(filename):
    """Memeriksa apakah ekstensi file diizinkan."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Membuka koneksi ke database SQLite."""
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row # Mengatur row_factory agar hasil query bisa diakses seperti dictionary
    return conn

def create_table():
    """Membuat tabel 'data_auten', 'data_belum_auten', dan 'users' di database jika belum ada."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabel untuk data autentikasi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_auten (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Nomor_Pensiun TEXT,
            Penerima TEXT,
            Status_Pensiun TEXT,
            Cabang TEXT,
            Mitra TEXT,
            Status_Auten TEXT,
            Waktu TEXT,
            Jenis_Pekerjaan TEXT,
            Usia INTEGER,
            cluster INTEGER
        )
    """)

    # Tabel untuk data belum autentikasi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_belum_auten (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Nomor_Pensiun TEXT,
            Penerima TEXT,
            Status_Pensiun TEXT,
            Cabang TEXT,
            Mitra TEXT,
            Bulan TEXT,
            Jenis_Pekerjaan TEXT,
            Usia INTEGER,
            cluster INTEGER
        )
    """)

    # Tabel 'users'
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


@app.cli.command('initdb')
def initdb_command():
    """Inisialisasi database dari command line (flask initdb)."""
    create_table()
    print('Database berhasil diinisialisasi.')

# --- Rute Utama yang Memeriksa Sesi Login ---
@app.route('/')
def home():
    """Mengelola pengalihan ke halaman login atau dashboard berdasarkan status sesi."""
    if 'logged_in' in session and session['logged_in']:
        if session['role'] == 'admin':
            return redirect(url_for('dashboard_admin'))
        else:
            return redirect(url_for('dashboard_user'))
    return render_template('login.html')

# --- Rute Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Menangani proses login pengguna."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and user['password'] == password: # Ingat: Untuk produksi, Anda HARUS menggunakan hashing password (misal: bcrypt) untuk keamanan!
            session['logged_in'] = True
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Berhasil login!', 'success')
            if session['role'] == 'admin':
                return redirect(url_for('dashboard_admin'))
            else:
                return redirect(url_for('dashboard_user'))
        else:
            flash('Username atau password salah.', 'error')
    return render_template('login.html')

# --- Rute Dashboard Admin ---
@app.route('/dashboard_admin')
def dashboard_admin():
    """Menampilkan halaman dashboard admin."""
    if 'logged_in' not in session or session['role'] != 'admin':
        flash('Anda tidak memiliki akses ke halaman ini.', 'error')
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- Rute Dashboard User ---
@app.route('/dashboard_user')
def dashboard_user():
    """Menampilkan halaman dashboard user."""
    if 'logged_in' not in session or session['role'] != 'user':
        flash('Anda tidak memiliki akses ke halaman ini.', 'error')
        return redirect(url_for('login'))
    return render_template('report.html') # Menggunakan report.html sebagai dashboard user

# --- Rute Logout ---
@app.route('/logout')
def logout():
    """Menangani proses logout pengguna."""
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('role', None)
    flash('Anda telah logout.', 'info')
    return redirect(url_for('login'))

@app.route('/clear_session')
def clear_session_debug():
    """Rute sementara untuk secara paksa menghapus sesi dari server."""
    session.clear() # Menghapus semua data dari sesi
    flash('Sesi telah dihapus secara paksa.', 'info')
    return redirect(url_for('login'))

# --- Rute Upload File (Mengembalikan table_name) ---
@app.route('/upload', methods=['POST'])
def upload_file():
    """Menangani upload file Excel dan memasukkan data ke database."""
    if 'logged_in' not in session or session['role'] != 'admin': # Hanya admin yang bisa upload
        return jsonify({'error': 'Unauthorized access'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada bagian file dalam request.'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Tidak ada file yang dipilih.'})

    if file and allowed_file(file.filename):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(f"File berhasil diupload: {filename}")

        try:
            df = pd.read_excel(filepath)
            print("Lima baris pertama dari DataFrame:")
            print(df.head().to_string())

            df.columns = (
                df.columns
                    .str.strip()
                    .str.lower()
                    .str.replace(' ', '_', regex=False)
            )
            print("Nama kolom setelah normalisasi:", df.columns.tolist())

            conn = get_db_connection()
            cursor = conn.cursor()

            table_name = None
            if 'status_auten' in df.columns and 'waktu' in df.columns:
                table_name = 'data_auten'
                # Optional: Hapus data lama di tabel yang dipilih sebelum memasukkan yang baru
                # cursor.execute(f"DELETE FROM {table_name}")
                # conn.commit()
                print(f"File diidentifikasi sebagai 'Autentikasi'. Mengupload ke tabel {table_name}.")
            elif 'bulan' in df.columns:
                table_name = 'data_belum_auten'
                # Optional: Hapus data lama di tabel yang dipilih sebelum memasukkan yang baru
                # cursor.execute(f"DELETE FROM {table_name}")
                # conn.commit()
                print(f"File diidentifikasi sebagai 'Belum Autentikasi'. Mengupload ke tabel {table_name}.")
            else:
                conn.close()
                os.remove(filepath)
                return jsonify({'error': 'Jenis file Excel tidak dikenali. Pastikan ada kolom "Status Auten" dan "Waktu" untuk data autentikasi, atau "Bulan" untuk data belum autentikasi.'})

            for index, row in df.iterrows():
                try:
                    if table_name == 'data_auten':
                        waktu_val = row.get('waktu')
                        if pd.notna(waktu_val):
                            if isinstance(waktu_val, datetime.time):
                                waktu_str = str(waktu_val)
                            else:
                                try:
                                    waktu_dt = pd.to_datetime(waktu_val)
                                    waktu_str = waktu_dt.strftime('%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    waktu_str = str(waktu_val)
                        else:
                            waktu_str = None

                        cursor.execute(f"""
                            INSERT INTO {table_name} (Nomor_Pensiun, Penerima, Status_Pensiun, Cabang, Mitra, Status_Auten, Waktu, Jenis_Pekerjaan, Usia)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            row.get('nomor_pensiun'),
                            row.get('penerima'),
                            row.get('status_pensiun'),
                            row.get('cabang'),
                            row.get('mitra'),
                            row.get('status_auten'),
                            waktu_str,
                            row.get('jenis_pekerjaan'),
                            row.get('usia')
                        ))
                    elif table_name == 'data_belum_auten':
                        cursor.execute(f"""
                            INSERT INTO {table_name} (Nomor_Pensiun, Penerima, Status_Pensiun, Cabang, Mitra, Bulan, Jenis_Pekerjaan, Usia)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            row.get('nomor_pensiun'),
                            row.get('penerima'),
                            row.get('status_pensiun'),
                            row.get('cabang'),
                            row.get('mitra'),
                            row.get('bulan'),
                            row.get('jenis_pekerjaan'),
                            row.get('usia')
                        ))
                except KeyError as e:
                    conn.rollback()
                    conn.close()
                    os.remove(filepath)
                    print(f"❌ Error: Kolom tidak ditemukan dalam file Excel untuk tipe file {table_name} - {e}")
                    return jsonify({'error': f'Error: Kolom tidak ditemukan dalam file Excel. Pastikan semua kolom yang dibutuhkan ada dan nama kolomnya benar (setelah dinormalisasi: huruf kecil, spasi diganti underscore): {e}'})
                except Exception as e:
                    conn.rollback()
                    conn.close()
                    os.remove(filepath)
                    print(f"❌ Error menyimpan baris data ke database - {e}")
                    return jsonify({'error': f'Error menyimpan data ke database - {e}'})

            conn.commit()

            preview_data = []
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 5")
            rows = cursor.fetchall()
            for row in rows:
                preview_data.append(dict(row))

            conn.close()
            os.remove(filepath)
            print(f"Data berhasil diupload dan disimpan ke tabel {table_name}.")
            # --- PENTING: Mengembalikan table_name di sini ---
            return jsonify({'message': f'Data berhasil diupload ke {table_name}!', 'preview_data': preview_data, 'uploaded_table': table_name})

        except pd.errors.EmptyDataError:
            if os.path.exists(filepath):
                os.remove(filepath)
            print("❌ Error: File Excel kosong atau tidak memiliki data.")
            return jsonify({'error': 'File Excel kosong atau tidak memiliki data.'})
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            print(f"❌ Terjadi kesalahan saat membaca atau memproses file Excel - {e}")
            return jsonify({'error': f'Terjadi kesalahan saat membaca atau memproses file Excel - {e}'})

    return jsonify({'error': 'Tipe file tidak valid. Harap unggah file .xlsx atau .xls.'})

@app.route('/cluster', methods=['POST'])
def cluster_data():
    """Melakukan K-Means clustering pada data dan mengembalikan hasilnya."""
    if 'logged_in' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 401

    data_request = request.get_json()
    k = data_request.get('k', 3)
    table_to_cluster = data_request.get('table', 'data_auten')

    print(f"\n--- Memulai Clustering untuk tabel: {table_to_cluster} dengan K={k} ---")

    conn = get_db_connection()
    df = pd.DataFrame() # Inisialisasi DataFrame kosong
    try:
        if table_to_cluster == 'data_auten':
            df = pd.read_sql_query("SELECT * FROM data_auten", conn)
        elif table_to_cluster == 'data_belum_auten':
            df = pd.read_sql_query("SELECT * FROM data_belum_auten", conn)
        else:
            print(f"❌ Error: Tabel untuk clustering tidak valid: {table_to_cluster}")
            return jsonify({'error': 'Tabel untuk clustering tidak valid.'})
    except Exception as e:
        print(f"❌ Error membaca data dari database: {e}")
        return jsonify({'error': f'Error membaca data dari database: {e}'})
    finally:
        conn.close()

    # --- PENTING: Normalisasi nama kolom setelah membaca dari database ---
    df.columns = (
        df.columns
            .str.strip()
            .str.lower()
            .str.replace(' ', '_', regex=False)
    )
    print("Nama kolom DataFrame setelah dinormalisasi (dari DB):", df.columns.tolist())


    print(f"Jumlah baris data dari DB: {len(df)}")
    if df.empty:
        print(f"❌ Error: Tidak ada data di tabel {table_to_cluster} untuk clustering.")
        return jsonify({'error': f'Tidak ada data di tabel {table_to_cluster} untuk clustering. Harap upload data terlebih dahulu.'})

    # --- Bagian Kritis: Memeriksa dan Memproses Kolom 'usia' ---
    if 'usia' not in df.columns:
        print("❌ Error: Kolom 'usia' tidak ditemukan dalam data dari DB setelah normalisasi.")
        return jsonify({'error': "Kolom 'usia' tidak ditemukan dalam data setelah dinormalisasi. Pastikan file Excel memiliki kolom usia."})
    
    df['usia'] = pd.to_numeric(df['usia'], errors='coerce')
    df = df.dropna(subset=['usia'])
    print(f"Jumlah baris setelah dropna 'usia': {len(df)}")

    if df.empty:
        print("❌ Error: Tidak ada data numerik yang valid setelah membersihkan kolom Usia. Clustering tidak dapat dilakukan.")
        return jsonify({'error': 'Tidak ada data numerik yang valid setelah membersihkan kolom Usia. Clustering tidak dapat dilakukan.'})

    cols_to_cluster = ['usia']
    categorical_cols_candidates = ['jenis_pekerjaan', 'status_pensiun'] # Nama kolom yang diharapkan setelah normalisasi

    df_filtered = df.copy()
    
    # --- Memproses Kolom Kategorikal secara Dinamis ---
    actual_categorical_cols = []
    for col in categorical_cols_candidates:
        if col in df_filtered.columns:
            actual_categorical_cols.append(col)
        else:
            print(f"Peringatan: Kolom kategorikal '{col}' tidak ditemukan dalam DataFrame. Melewatkan encoding.")

    if not actual_categorical_cols:
        print("Peringatan: Tidak ada kolom kategorikal yang ditemukan untuk encoding. Hanya menggunakan 'usia' untuk clustering.")
        df_encoded = df_filtered[cols_to_cluster].copy()
    else:
        print(f"Kolom kategorikal yang akan di-encode: {actual_categorical_cols}")
        for col in actual_categorical_cols:
            df_filtered[col] = df_filtered[col].astype(str).fillna('UNKNOWN') # Mengisi NaN dengan 'UNKNOWN'
        
        df_encoded = pd.get_dummies(df_filtered, columns=actual_categorical_cols, drop_first=True)
        # --- NEW: Explicitly convert boolean dtypes to int (0 or 1) ---
        for col in df_encoded.columns:
            if df_encoded[col].dtype == bool:
                df_encoded[col] = df_encoded[col].astype(int)
        # --- END NEW ---

        encoded_cols = [col for col in df_encoded.columns if any(col.startswith(cat + '_') for cat in actual_categorical_cols)]
        cols_to_cluster.extend(encoded_cols)
    
    print(f"Jumlah kolom di df_encoded sebelum filtering final_cols_to_cluster: {df_encoded.shape[1]}")

    final_cols_to_cluster = [col for col in cols_to_cluster if col in df_encoded.columns]
    print(f"Kolom final untuk clustering: {final_cols_to_cluster}")


    if not final_cols_to_cluster:
        print('❌ Error: Tidak ada kolom yang valid (Usia atau kategorikal) untuk clustering setelah encoding.')
        return jsonify({'error': 'Tidak ada kolom yang valid (Usia atau kategorikal) untuk clustering setelah encoding. Pastikan data memiliki kolom Usia dan kolom kategorikal yang benar.'})

    df_cluster = df_encoded[final_cols_to_cluster].copy()
    
    # Mengisi nilai NaN yang mungkin muncul setelah get_dummies atau karena kolom numerik lain
    # Gunakan mean hanya pada kolom numerik dari df_cluster
    for col in df_cluster.columns:
        if pd.api.types.is_numeric_dtype(df_cluster[col]):
            df_cluster[col] = df_cluster[col].fillna(df_cluster[col].mean())
    
    print(f"Jumlah baris df_cluster sebelum scaling: {len(df_cluster)}")
    print(f"Kolom df_cluster sebelum scaling: {df_cluster.columns.tolist()}")
    print("df_cluster head sebelum scaling:")
    print(df_cluster.head().to_string())


    # Periksa apakah ada kolom di df_cluster yang semuanya NaN atau inf
    # Cek nilai Inf atau NaN secara lebih spesifik
    if df_cluster.isnull().values.any():
        print("❌ Error: df_cluster mengandung nilai NaN setelah fillna.")
        return jsonify({'error': 'Data untuk clustering mengandung nilai NaN setelah pemrosesan. Pastikan semua kolom numerik valid.'})
    # This check caused the error, let's re-verify it with the new conversion
    if not df_cluster.apply(pd.api.types.is_numeric_dtype).all():
        print("❌ Error: df_cluster mengandung nilai non-numerik setelah konversi.")
        # This will print the exact non-numeric columns if any
        non_numeric_cols = [col for col in df_cluster.columns if not pd.api.types.is_numeric_dtype(df_cluster[col])]
        print(f"Kolom non-numerik terdeteksi: {non_numeric_cols}")
        return jsonify({'error': 'Data untuk clustering mengandung nilai non-numerik setelah pemrosesan. Pastikan semua kolom numerik valid.'})
    if (df_cluster == float('inf')).values.any() or (df_cluster == float('-inf')).values.any():
        print("❌ Error: df_cluster mengandung nilai Inf.")
        return jsonify({'error': 'Data untuk clustering mengandung nilai Inf setelah pemrosesan. Pastikan semua kolom numerik valid.'})
    
    # Pastikan df_cluster tidak kosong sebelum scaling
    if df_cluster.empty:
        print("❌ Error: df_cluster menjadi kosong sebelum scaling.")
        return jsonify({'error': 'Data untuk clustering menjadi kosong sebelum scaling. Tidak dapat melakukan clustering.'})

    scaler = StandardScaler()
    try:
        df_scaled = scaler.fit_transform(df_cluster)
        print(f"Shape df_scaled: {df_scaled.shape}")
    except ValueError as e:
        print(f"❌ Error saat melakukan scaling: {e}. Periksa apakah ada nilai non-numerik yang tersisa di df_cluster atau varian nol.")
        return jsonify({'error': f'Error saat melakukan scaling: {e}. Pastikan semua data numerik valid dan memiliki variansi.'})

    try:
        # Menambahkan pengecekan untuk memastikan jumlah sampel >= jumlah cluster
        if df_scaled.shape[0] < k:
            print(f"❌ Error: Jumlah data yang valid ({df_scaled.shape[0]} baris) kurang dari jumlah cluster yang diminta ({k}).")
            return jsonify({'error': f'Jumlah data yang valid ({df_scaled.shape[0]} baris) kurang dari jumlah cluster yang diminta ({k}). Tingkatkan jumlah data atau kurangi K.'})
        
        kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
        df_encoded['cluster'] = kmeans.fit_predict(df_scaled)
        print("Clustering (KMeans.fit_predict) berhasil dilakukan.")

        conn_update = get_db_connection()
        cursor_update = conn_update.cursor()
        print(f"Memulai update database untuk {len(df_encoded)} baris...")
        for index, row in df_encoded.iterrows():
            if 'id' in row and not pd.isna(row['id']):
                try:
                    record_id = int(row['id'])
                except ValueError:
                    print(f"Peringatan: ID '{row['id']}' tidak dapat diubah menjadi integer. Melewatkan baris ini.")
                    continue
                # Pastikan kolom 'cluster' ada dan valid
                if 'cluster' in row and not pd.isna(row['cluster']):
                    cursor_update.execute(f"UPDATE {table_to_cluster} SET cluster = ? WHERE id = ?", (int(row['cluster']), record_id))
                else:
                    print(f"Peringatan: Cluster label untuk ID {record_id} tidak valid. Melewatkan update.")
            else:
                print(f"Peringatan: Baris ke-{index} tidak memiliki ID yang valid. Melewatkan update.")
        conn_update.commit()
        conn_update.close()
        print(f"Cluster labels berhasil disimpan ke tabel {table_to_cluster}.")

        # Kolom yang akan dikembalikan ke frontend
        result_cols = ['nomor_pensiun', 'penerima', 'status_pensiun', 'jenis_pekerjaan', 'usia', 'cluster']
        if table_to_cluster == 'data_auten':
            result_cols.append('waktu')
        elif table_to_cluster == 'data_belum_auten':
            result_cols.append('bulan')

        # Filter result_cols agar hanya menyertakan kolom yang benar-benar ada di df_encoded
        # Penting: 'id' juga mungkin dibutuhkan oleh frontend jika Anda ingin menampilkan atau melakukan operasi berdasarkan ID.
        result_cols = [col for col in result_cols if col in df_encoded.columns]
        print(f"Kolom hasil akhir yang akan dikirim: {result_cols}")

        result = df_encoded[result_cols].to_dict(orient='records')
        
        # --- DEBUGGING: Cetak hasil sebelum dikirim ke frontend ---
        print("\n--- Hasil Clustering yang Dikirim ke Frontend ---")
        if result: # Cek jika list tidak kosong sebelum mencetak bagiannya
            print(result[:5]) # Cetak 5 baris pertama saja untuk menghindari output terlalu panjang
        else:
            print("Hasil clustering kosong.")
        print(f"Total baris hasil clustering: {len(result)}")
        print("--------------------------------------------------\n")

        return jsonify(result)
    except ValueError as e:
        print(f"❌ Error saat melakukan clustering (ValueError): {e}")
        return jsonify({'error': f'Error saat melakukan clustering: {e}. Pastikan Anda memiliki cukup data dan nilai numerik yang valid.'})
    except Exception as e:
        print(f"❌ Terjadi kesalahan tak terduga saat clustering: {e}")
        return jsonify({'error': f'Terjadi kesalahan tak terduga saat clustering: {e}'})


# --- Rute API untuk Mengambil Data dari Database ---
@app.route('/api/data_auten')
def get_data_auten():
    """Mengambil semua data dari tabel data_auten."""
    if 'logged_in' not in session: # Tidak perlu cek role jika data ini bisa diakses user/admin
        return jsonify({'error': 'Unauthorized access'}), 401 # Atau bisa diakses publik jika tidak sensitif

    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM data_auten", conn)
    conn.close()
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/data_belum_auten')
def get_data_belum_auten():
    """Mengambil semua data dari tabel data_belum_auten."""
    if 'logged_in' not in session: # Tidak perlu cek role jika data ini bisa diakses user/admin
        return jsonify({'error': 'Unauthorized access'}), 401 # Atau bisa diakses publik jika tidak sensitif

    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM data_belum_auten", conn)
    conn.close()
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/clustered_data/<string:table_name>')
def get_clustered_data(table_name):
    """Mengambil data yang sudah di-cluster dari database."""
    if 'logged_in' not in session: # Bisa diakses admin atau user
        return jsonify({'error': 'Unauthorized access'}), 401

    if table_name not in ['data_auten', 'data_belum_auten']:
        return jsonify({'error': 'Tabel tidak valid.'}), 400

    conn = get_db_connection()
    df = pd.read_sql_query(f"SELECT Nomor_Pensiun, Penerima, Status_Pensiun, Jenis_Pekerjaan, Usia, cluster FROM {table_name}", conn)
    conn.close()

    if df.empty:
        return jsonify({'message': f'Tidak ada data di tabel {table_name} atau belum di-cluster.'})

    return jsonify(df.to_dict(orient='records'))

# --- Rute Statistik ---
@app.route('/statistics')
def get_statistics():
    """Mengambil data statistik klaim dari database."""
    if 'logged_in' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 401

    conn = get_db_connection()
    try:
        total_claims = conn.execute("SELECT COUNT(*) FROM data_auten").fetchone()[0]
        pension_claims = conn.execute("SELECT COUNT(*) FROM data_auten WHERE Status_Pensiun = 'Pensiun'").fetchone()[0]
        accident_claims = conn.execute("SELECT COUNT(*) FROM data_auten WHERE Status_Pensiun = 'Kecelakaan'").fetchone()[0]
        death_claims = conn.execute("SELECT COUNT(*) FROM data_auten WHERE Status_Pensiun = 'Kematian'").fetchone()[0]

    except sqlite3.Error as e:
        print(f"Database error in get_statistics: {e}")
        return jsonify({'error': 'Database error occurred while fetching statistics.'}), 500
    finally:
        conn.close()

    return jsonify({
        'total_claims': total_claims,
        'pension_claims': pension_claims,
        'accident_claims': accident_claims,
        'death_claims': death_claims
    })


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    create_table()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', 'adminpass', 'admin'))
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ('user', 'userpass', 'user'))
    conn.commit()
    conn.close()
    app.run(debug=True)

