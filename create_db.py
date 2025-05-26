import mysql.connector

def create_table(db_config, table_name):
    """Membuat tabel di database MySQL."""
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        if "belum_auten" in table_name:
            query = f"""
                CREATE TABLE IF NOT EXISTS `{table_name}` (
                    Nomor_Pensiun VARCHAR(255),
                    Penerima VARCHAR(255),
                    Status_Pensiun VARCHAR(255),
                    Cabang VARCHAR(255),
                    Mitra VARCHAR(255),
                    Bulan VARCHAR(255),
                    Jenis_Pekerjaan VARCHAR(255),
                    Usia INT
                );
                ALTER TABLE `{table_name}` ADD COLUMN IF NOT EXISTS Jenis_Pekerjaan VARCHAR(255);
                ALTER TABLE `{table_name}` ADD COLUMN IF NOT EXISTS Usia INT;
            """
        else:
            query = f"""
                CREATE TABLE IF NOT EXISTS `{table_name}` (
                    Nomor_Pensiun VARCHAR(255),
                    Penerima VARCHAR(255),
                    Status_Pensiun VARCHAR(255),
                    Cabang VARCHAR(255),
                    Mitra VARCHAR(255),
                    Status_Auten VARCHAR(255),
                    Waktu VARCHAR(255),
                    Jenis_Pekerjaan VARCHAR(255),
                    Usia INT
                );
                ALTER TABLE `{table_name}` ADD COLUMN IF NOT EXISTS Jenis_Pekerjaan VARCHAR(255);
                 ALTER TABLE `{table_name}` ADD COLUMN IF NOT EXISTS Usia INT;
            """

        for result in cursor.execute(query, multi=True):
            if result.has_rows():
                print(result.fetchall())
        conn.commit()
        print(f"Tabel {table_name} berhasil dibuat/dimodifikasi.")

    except mysql.connector.Error as e:
        print(f"Terjadi kesalahan MySQL saat membuat/memodifikasi tabel {table_name}: {e}")
    except Exception as e:
        print(f"Terjadi kesalahan lain saat membuat/memodifikasi tabel {table_name}: {e}")
    finally:
        if conn:
            conn.close()

db_config = {
    "host": "localhost",
    "user": "Salshananditya",
    "password": "N4tush@@a",
    "database": "data_auten_asabri"
}

table_names = [
    "auten_april",
    "auten_juli",
    "auten_juni",
    "auten_mei",
    "belum_auten_april",
    "belum_auten_juli",
    "belum_auten_juni",
    "belum_auten_mei"
]

for table_name in table_names:
    create_table(db_config, table_name)