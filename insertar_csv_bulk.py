import psycopg2
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

def valores(cursor, filas, campos):
    patron = "(%s" + ",%s" * (campos - 1) + ")"
    return ','.join(cursor.mogrify(patron, fila).decode('utf-8') for fila in filas)

def construir_filas(cursor, batch, role_map):
    for username, _, _, _, _, _, _, role in batch:
        if role not in role_map:
            raise ValueError(f"Rol sin correspondencia en la tabla roles: {role!r} (username={username})")

    ud_ids = proximos_ids(cursor, 'users_data', len(batch))
    u_ids = proximos_ids(cursor, 'users', len(batch))

    filas_users_data = [
        (ud_ids[i], row[2], row[3], row[4], row[5]) for i, row in enumerate(batch)
    ]
    filas_users = [
        (u_ids[i], row[0], row[1], row[6], ud_ids[i]) for i, row in enumerate(batch)
    ]
    filas_user_roles = [
        (u_ids[i], role_map[row[7]]) for i, row in enumerate(batch)
    ]
    return filas_users_data, filas_users, filas_user_roles

def insertar_desde_csv_batch(connection_params, csv_path, batch_size=100000):
    conn = psycopg2.connect(**connection_params)
    cursor = conn.cursor()

    try:
        role_map = preparar_roles(cursor)
        conn.commit()

        print(f"Leyendo archivo: {csv_path}")

        inicio = time.time()
        total_insertados = 0
        errores = 0

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
                    try:
                        filas_users_data, filas_users, filas_user_roles = construir_filas(
                            cursor, batch, role_map
                        )

                        cursor.execute(f"""
                            INSERT INTO users_data (id, first_name, last_name, address, phone_number)
                            VALUES {valores(cursor, filas_users_data, 5)}
                        """)
                        cursor.execute(f"""
                            INSERT INTO users (id, username, email, active, user_data_id)
                            VALUES {valores(cursor, filas_users, 5)}
                        """)
                        cursor.execute(f"""
                            INSERT INTO user_roles (user_id, role_id)
                            VALUES {valores(cursor, filas_user_roles, 2)}
                        """)

                        conn.commit()
                        total_insertados += len(batch)

                        elapsed = time.time() - inicio
                        velocidad = total_insertados / elapsed if elapsed > 0 else 0
                        print(f"  Insertados: {total_insertados:,} registros - {velocidad:,.0f} registros/seg")

                    except Exception as e:
                        conn.rollback()
                        errores += len(batch)
                        print(f"  Error en lote: {e}")

                    batch = []

            if batch:
                try:
                    filas_users_data, filas_users, filas_user_roles = construir_filas(
                        cursor, batch, role_map
                    )

                    cursor.execute(f"""
                        INSERT INTO users_data (id, first_name, last_name, address, phone_number)
                        VALUES {valores(cursor, filas_users_data, 5)}
                    """)
                    cursor.execute(f"""
                        INSERT INTO users (id, username, email, active, user_data_id)
                        VALUES {valores(cursor, filas_users, 5)}
                    """)
                    cursor.execute(f"""
                        INSERT INTO user_roles (user_id, role_id)
                        VALUES {valores(cursor, filas_user_roles, 2)}
                    """)

                    conn.commit()
                    total_insertados += len(batch)

                except Exception as e:
                    conn.rollback()
                    errores += len(batch)
                    print(f"  Error en ultimo lote: {e}")

        fin = time.time()
        tiempo_total = fin - inicio

        print(f"\n{'='*50}")
        print(f"COMPLETADO")
        print(f"{'='*50}")
        print(f"Total insertados: {total_insertados:,}")
        print(f"Errores: {errores:,}")
        print(f"Tiempo total: {tiempo_total:.2f} segundos")
        print(f"Velocidad promedio: {total_insertados / tiempo_total:,.0f} registros/segundo")

        for tabla in ('users', 'users_data', 'user_roles', 'roles'):
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            total = cursor.fetchone()[0]
            print(f"Total en {tabla}: {total:,}")

    except Exception as e:
        conn.rollback()
        print(f"Error general: {e}")
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

    insertar_desde_csv_batch(DB_CONFIG, CSV_PATH, BATCH_SIZE)
