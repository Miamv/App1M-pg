import csv
import sys

def diagnosticar_csv(csv_path):
    print(f"Diagnosticando archivo: {csv_path}")
    print("=" * 60)
    
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        headers = reader.fieldnames
        print(f"Columnas encontradas ({len(headers)}):")
        for i, header in enumerate(headers, 1):
            print(f"  {i}. {header}")
        
        print("\nMuestra de datos (primeras 3 filas):")
        print("-" * 60)
        
        for i, row in enumerate(reader):
            if i >= 3:
                break
            print(f"\nFila {i+1}:")
            for key, value in row.items():
                valor_preview = value[:50] + "..." if len(value) > 50 else value
                print(f"  {key}: {valor_preview}")
        
        csvfile.seek(0)
        next(csvfile)
        total_filas = sum(1 for _ in csvfile)
        
        print(f"\n{'=' * 60}")
        print(f"Total de registros: {total_filas:,}")
        print(f"{'=' * 60}")
        
        print("\nMapeo sugerido para PostgreSQL:")
        print("-" * 60)
        mapeo = {
            'username': 'VARCHAR(150) UNIQUE NOT NULL',
            'email': 'VARCHAR(200) UNIQUE NOT NULL',
            'firstName': 'VARCHAR(100) NOT NULL',
            'lastName': 'VARCHAR(100) NOT NULL',
            'address': 'TEXT',
            'phoneNumber': 'VARCHAR(50)',
            'active': 'BOOLEAN DEFAULT true',
            'role': 'VARCHAR(50) DEFAULT \'guest\''
        }
        
        for col in headers:
            tipo = mapeo.get(col, 'TEXT')
            print(f"  {col} -> {tipo}")

if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'usuarios_bulk.csv'
    diagnosticar_csv(csv_path)
