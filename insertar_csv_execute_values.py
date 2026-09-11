import psycopg2
from psycopg2.extras import execute_values
import csv
import time
import sys
import os
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

def insertar_csv_execute_values(connection_params, csv_path, batch_size=10000):
    conn = psycopg2.connect(**connection_params)
    cursor = conn.cursor()
    
    try:
        crear_tabla_si_no_existe(cursor)
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
                    execute_values(
                        cursor,
                        """INSERT INTO usuarios (username, email, first_name, last_name, address, phone_number, active, role)
                           VALUES %s
                           ON CONFLICT (username) DO UPDATE SET
                               email = EXCLUDED.email,
                               first_name = EXCLUDED.first_name,
                               last_name = EXCLUDED.last_name,
                               address = EXCLUDED.address,
                               phone_number = EXCLUDED.phone_number,
                               active = EXCLUDED.active,
                               role = EXCLUDED.role""",
                        batch,
                        page_size=batch_size
                    )
                    
                    conn.commit()
                    total_insertados += len(batch)
                    
                    elapsed = time.time() - inicio
                    velocidad = total_insertados / elapsed if elapsed > 0 else 0
                    print(f"  Insertados: {total_insertados:,} registros - {velocidad:,.0f} registros/seg")
                    
                    batch = []
            
            if batch:
                execute_values(
                    cursor,
                    """INSERT INTO usuarios (username, email, first_name, last_name, address, phone_number, active, role)
                       VALUES %s
                       ON CONFLICT (username) DO UPDATE SET
                           email = EXCLUDED.email,
                           first_name = EXCLUDED.first_name,
                           last_name = EXCLUDED.last_name,
                           address = EXCLUDED.address,
                           phone_number = EXCLUDED.phone_number,
                           active = EXCLUDED.active,
                           role = EXCLUDED.role""",
                    batch,
                    page_size=len(batch)
                )
                
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
        
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_en_tabla = cursor.fetchone()[0]
        print(f"Total de registros en la tabla: {total_en_tabla:,}")
        
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
