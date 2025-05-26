import os
import pandas as pd
import mysql.connector
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

db_config = {
    "host": "localhost",
    "user": "Salshananditya",
    "password": "N4tush@@a",
    "database": "data_auten_asabri"
}

excel_directory = "C:/Users/Hp 840 G1/Documents/Data Auten Salsha"

tables_with_status_auten   = ["auten_april", "auten_mei", "auten_juni", "auten_juli"]
tables_without_status_auten = ["belum_auten_april", "belum_auten_mei", "belum_auten_juni", "belum_auten_juli"]

def insert_data(file_path, table_name, has_status_auten):
    conn = None
    try:
        logging.debug(f"📄 Memproses file: {file_path}")

    
        df = pd.read_excel(file_path)

        df.columns = (
            df.columns
              .str.strip()
              .str.lower()
              .str.replace(' ', '_', regex=False)
        )
        logging.debug(f"📑 Kolom yang ditemukan: {df.columns.tolist()}")

        # Validasi kolom
        expected = {"nomor_pensiun", "penerima", "status_pensiun", "cabang", "mitra"}
        if has_status_auten:
            expected |= {"status_auten", "waktu"}  # union
        else:
            expected.add("bulan")

        if not expected.issubset(set(df.columns)):
            logging.error(f"❌ {file_path} tidak memiliki semua kolom yang diperlukan.")
            logging.error(f"    Ditemukan: {set(df.columns)}")
            logging.error(f"    Diperlukan: {expected}")
            return

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()


        for _, row in df.iterrows():
            if has_status_auten:
        
                waktu_val = row.get("waktu")
                if pd.isna(waktu_val):
                    waktu_mysql = None
                else:

                    for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                        try:
                            waktu_obj = datetime.strptime(str(waktu_val), fmt)
                            waktu_mysql = waktu_obj.strftime("%Y-%m-%d %H:%M:%S")
                            break
                        except ValueError:
                            waktu_mysql = None

                sql = (
                    f"INSERT INTO `{table_name}` "
                    "(`Nomor_Pensiun`,`Penerima`,`Status_Pensiun`,`Cabang`,`Mitra`,`Status_Auten`,`Waktu`) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)"
                )
                values = (
                    row["nomor_pensiun"], row["penerima"], row["status_pensiun"],
                    row["cabang"], row["mitra"], row["status_auten"], waktu_mysql
                )
            else:
                sql = (
                    f"INSERT INTO `{table_name}` "
                    "(`Nomor_Pensiun`,`Penerima`,`Status_Pensiun`,`Cabang`,`Mitra`,`Bulan`) "
                    "VALUES (%s,%s,%s,%s,%s,%s)"
                )
                values = (
                    row["nomor_pensiun"], row["penerima"], row["status_pensiun"],
                    row["cabang"], row["mitra"], row["bulan"]
                )

            try:
                cursor.execute(sql, values)
                logging.debug(f"✅ Baris dimasukkan ke {table_name}: {values}")
            except Exception:
                logging.error(f"❌ Gagal memasukkan baris ke {table_name}: {values}")
                logging.exception("Error saat INSERT")

        conn.commit()
        logging.info(f"✅ Selesai memasukkan data ke {table_name}")

    except PermissionError:
        logging.error(f"❌ Tidak bisa membaca file {file_path}, pastikan tidak sedang dibuka.")
    except Exception:
        logging.error(f"❌ Terjadi kesalahan saat memproses {file_path}")
        logging.exception("Error utama")
    finally:
        if conn:
            conn.close()


if not os.path.isdir(excel_directory):
    logging.error(f"❌ Folder {excel_directory} tidak ditemukan. Abort.")
    exit(1)

for fname in os.listdir(excel_directory):
    if not fname.lower().endswith(".xlsx"):
        continue
    raw = os.path.splitext(fname)[0].lower()
    normalized = raw.replace(" ", "_")
    file_path = os.path.join(excel_directory, fname)

    if normalized in tables_with_status_auten:
        insert_data(file_path, normalized, has_status_auten=True)
    elif normalized in tables_without_status_auten:
        insert_data(file_path, normalized, has_status_auten=False)
