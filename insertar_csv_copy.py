import psycopg2
import os
import time
import sys
from dotenv import load_dotenv

load_dotenv()

def crear_tabla_si_no_existe(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username VARCHAR(150) UNIQUE NOT NULL,
            email VARCHAR(200) UNIQUE NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            address TEXT,
            phone_number VARCHAR(50),
            active BOOLEAN DEFAULT true,
            role VARCHAR(50) DEFAULT 'guest',
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def insertar_csv_con_copy(connection_params, csv_path, skip_header=True):
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
        
        print(f"Insertando CSV usando COPY: {csv_path}")
        inicio = time.time()
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            if skip_header:
                next(f)
            
            cursor.copy_expert("""
                COPY usuarios (username, email, first_name, last_name, address, phone_number, active, role) 
                FROM STDIN WITH (FORMAT csv, HEADER false, DELIMITER ',', QUOTE '"', ESCAPE '"')
            """, f)
        
        conn.commit()
        
        fin = time.time()
        tiempo_total = fin - inicio
        
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_insertados = cursor.fetchone()[0]
        
        print(f"\n{'='*50}")
        print(f"COMPLETADO")
        print(f"{'='*50}")
        print(f"Total insertados: {total_insertados:,}")
        print(f"Tiempo total: {tiempo_total:.2f} segundos")
        print(f"Velocidad: {total_insertados / tiempo_total:,.0f} registros/segundo")
        
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
        'database': os.getenv('DB_NAME', 'USERS_AUTH_DEV'),
        'user': os.getenv('DB_USER', 'picante'),
        'password': os.getenv('DB_PASSWORD', ''),
        'port': int(os.getenv('DB_PORT', '5433'))
    }
    
    CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else 'usuarios_bulk.csv'
    
    insertar_csv_con_copy(DB_CONFIG, CSV_PATH)
