import psycopg2
from psycopg2.extras import execute_values
import csv
import time
import sys
import os
from dotenv import load_dotenv

load_dotenv()

def preparar_roles(cursor):
    cursor.execute("""
        INSERT INTO roles (description) VALUES ('guest'), ('admin'), ('manager')
        ON CONFLICT (description) DO NOTHING
    """)
    cursor.execute("SELECT description, id FROM roles")
    return dict(cursor.fetchall())

def proximos_ids(cursor, tabla, cantidad):
    cursor.execute(
        "SELECT nextval(pg_get_serial_sequence(%s, 'id')) FROM generate_series(1, %s)",
        (tabla, cantidad),
    )
    return [row[0] for row in cursor.fetchall()]

def insertar_lote(cursor, batch, role_map):
    for username, _, _, _, _, _, _, role in batch:
        if role not in role_map:
            raise ValueError(f"Rol sin correspondencia en la tabla roles: {role!r} (username={username})")

    ud_ids = proximos_ids(cursor, 'users_data', len(batch))
    u_ids = proximos_ids(cursor, 'users', len(batch))

    execute_values(
        cursor,
        "INSERT INTO users_data (id, first_name, last_name, address, phone_number) VALUES %s",
        [(ud_ids[i], row[2], row[3], row[4], row[5]) for i, row in enumerate(batch)],
        page_size=len(batch),
    )
    execute_values(
        cursor,
        "INSERT INTO users (id, username, email, active, user_data_id) VALUES %s",
        [(u_ids[i], row[0], row[1], row[6], ud_ids[i]) for i, row in enumerate(batch)],
        page_size=len(batch),
    )
    execute_values(
        cursor,
        "INSERT INTO user_roles (user_id, role_id) VALUES %s",
        [(u_ids[i], role_map[row[7]]) for i, row in enumerate(batch)],
        page_size=len(batch),
    )

def insertar_csv_execute_values(connection_params, csv_path, batch_size=10000):
    conn = psycopg2.connect(**connection_params)
    cursor = conn.cursor()

    try:
        role_map = preparar_roles(cursor)
        conn.commit()

        print(f"Insertando CSV usando execute_values: {csv_path}")
        print(f"Lote: {batch_size:,} registros")

        inicio = time.time()
        total_insertados = 0

        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            batch = []

            for row in reader:
                batch.append((
                    row['username'],
                    row['email'],
                    row['firstName'],
                    row['lastName'],
                    row['address'],
                    row['phoneNumber'],
                    row['active'].lower() == 'true',
                    row['role']
                ))

                if len(batch) >= batch_size:
                    insertar_lote(cursor, batch, role_map)

                    conn.commit()
                    total_insertados += len(batch)

                    elapsed = time.time() - inicio
                    velocidad = total_insertados / elapsed if elapsed > 0 else 0
                    print(f"  Insertados: {total_insertados:,} registros - {velocidad:,.0f} registros/seg")

                    batch = []

            if batch:
                insertar_lote(cursor, batch, role_map)

                conn.commit()
                total_insertados += len(batch)

        fin = time.time()
        tiempo_total = fin - inicio

        print(f"\n{'='*50}")
        print(f"COMPLETADO")
        print(f"{'='*50}")
        print(f"Total insertados: {total_insertados:,}")
        print(f"Tiempo total: {tiempo_total:.2f} segundos")
        print(f"Velocidad promedio: {total_insertados / tiempo_total:,.0f} registros/segundo")

        for tabla in ('users', 'users_data', 'user_roles', 'roles'):
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            total = cursor.fetchone()[0]
            print(f"Total en {tabla}: {total:,}")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', ''),
        'user': os.getenv('DB_USER', ''),
        'password': os.getenv('DB_PASSWORD', ''),
        'port': int(os.getenv('DB_PORT', '5432'))
    }

    CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else 'usuarios_bulk.csv'
    BATCH_SIZE = int(sys.argv[2]) if len(sys.argv) > 2 else 10000

    insertar_csv_execute_values(DB_CONFIG, CSV_PATH, BATCH_SIZE)
