import psycopg2
import os
import time
import sys
from dotenv import load_dotenv

load_dotenv()

def preparar_roles(cursor):
    cursor.execute("""
        INSERT INTO roles (description) VALUES ('guest'), ('admin'), ('manager')
        ON CONFLICT (description) DO NOTHING
    """)
    cursor.execute("SELECT description, id FROM roles")
    return dict(cursor.fetchall())

def insertar_csv_con_copy(connection_params, csv_path):
    try:
        conn = psycopg2.connect(**connection_params)
    except psycopg2.OperationalError as error:
        mensaje = str(error).strip() or "PostgreSQL rechazó la conexión sin indicar el motivo."
        print("No se pudo conectar a PostgreSQL.")
        print(f"  Servidor: {connection_params['host']}:{connection_params['port']}")
        print(f"  Base de datos: {connection_params['database']}")
        print(f"  Usuario: {connection_params['user']}")
        print(f"  Motivo: {mensaje}")
        print("\nComprueba que PostgreSQL esté iniciado, que exista la base de datos y que")
        print("PGPASSWORD contenga la contraseña correcta del usuario indicado.")
        raise SystemExit(1) from None

    cursor = conn.cursor()

    try:
        conn.commit()

        role_map = preparar_roles(cursor)

        print(f"Insertando CSV usando COPY: {csv_path}")

        cursor.execute("""
            CREATE TEMP TABLE stage (
                username varchar(255),
                email varchar(255),
                first_name varchar(255),
                last_name varchar(255),
                address varchar(255),
                phone_number varchar(255),
                active boolean,
                role varchar(64),
                seq bigserial,
                u_id bigint,
                ud_id bigint,
                role_id bigint
            )
        """)

        inicio = time.time()

        with open(csv_path, 'r', encoding='utf-8') as f:
            cursor.copy_expert("""
                COPY stage (username, email, first_name, last_name, address, phone_number, active, role)
                FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ',', QUOTE '"', ESCAPE '"')
            """, f)

        cursor.execute("SELECT count(*) FROM stage")
        total_filas = cursor.fetchone()[0]
        print(f"Filas leídas del CSV: {total_filas:,}")

        cursor.execute("""
            UPDATE stage s SET role_id = r.id
            FROM roles r WHERE r.description = s.role
        """)
        cursor.execute("SELECT count(*) FROM stage WHERE role_id IS NULL")
        sin_rol = cursor.fetchone()[0]
        if sin_rol:
            raise RuntimeError(
                f"{sin_rol:,} filas del CSV tienen un 'role' sin correspondencia en la tabla roles"
            )

        cursor.execute(
            "UPDATE stage SET ud_id = nextval(pg_get_serial_sequence('users_data', 'id'))"
        )
        cursor.execute(
            "UPDATE stage SET u_id = nextval(pg_get_serial_sequence('users', 'id'))"
        )
        conn.commit()

        chunk = 100000
        procesadas = 0
        for desde in range(0, total_filas, chunk):
            hasta = desde + chunk
            cursor.execute("""
                INSERT INTO users_data (id, first_name, last_name, address, phone_number)
                SELECT ud_id, first_name, last_name, address, phone_number
                FROM stage WHERE seq > %s AND seq <= %s
            """, (desde, hasta))
            cursor.execute("""
                INSERT INTO users (id, username, email, active, user_data_id)
                SELECT u_id, username, email, active, ud_id
                FROM stage WHERE seq > %s AND seq <= %s
            """, (desde, hasta))
            cursor.execute("""
                INSERT INTO user_roles (user_id, role_id)
                SELECT u_id, role_id
                FROM stage WHERE seq > %s AND seq <= %s
            """, (desde, hasta))
            conn.commit()

            procesadas = min(hasta, total_filas)
            elapsed = time.time() - inicio
            velocidad = procesadas / elapsed if elapsed > 0 else 0
            print(f"  Insertados: {procesadas:,} registros - {velocidad:,.0f} registros/seg")

        fin = time.time()
        tiempo_total = fin - inicio

        print(f"\n{'='*50}")
        print(f"COMPLETADO")
        print(f"{'='*50}")
        for tabla in ('users', 'users_data', 'user_roles', 'roles'):
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            total = cursor.fetchone()[0]
            print(f"Total en {tabla}: {total:,}")
        print(f"Tiempo total: {tiempo_total:.2f} segundos")
        print(f"Velocidad: {total_filas / tiempo_total:,.0f} registros/segundo")

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

    insertar_csv_con_copy(DB_CONFIG, CSV_PATH)
