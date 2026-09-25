# Bulk Insert PostgreSQL - Inserción Masiva de Usuarios

Script Python para inserción masiva de registros en PostgreSQL utilizando `psycopg2` y `copy_expert` para máximo rendimiento.

## Requisitos Previos

- Python 3.8 o superior
- PostgreSQL 12 o superior (o Docker)
- pip (gestor de paquetes de Python)

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Miamv/App1M-pg.git
cd App1M-pg
```

### 2. Crear entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar el archivo .env con tus datos de conexión
```

**Variables de entorno:**

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DB_HOST` | Host de PostgreSQL | `localhost` |
| `DB_PORT` | Puerto de PostgreSQL | `5432` |
| `DB_NAME` | Nombre de la base de datos | `mi_base_datos` |
| `DB_USER` | Usuario de PostgreSQL | `mi_usuario` |
| `DB_PASSWORD` | Contraseña del usuario | `mi_contraseña` |

## Uso

### Insertar desde archivo CSV

```bash
python insertar_csv_copy.py ruta/archivo.csv
```

### Opciones disponibles

| Script | Método | Velocidad | Descripción |
|--------|--------|-----------|-------------|
| `insertar_csv_copy.py` | COPY | ~200K-500K/s | El más rápido (recomendado) |
| `insertar_csv_execute_values.py` | execute_values | ~100K-200K/s | Rápido y flexible |
| `insertar_csv_bulk.py` | SQL puro | ~50K-100K/s | Control total |

### Ejemplos

```bash
# Insertar 1 millón de registros
python insertar_csv_copy.py usuarios_bulk.csv

# Insertar con tamaño de lote personalizado
python insertar_csv_execute_values.py usuarios_bulk.csv 10000

# Diagnosticar estructura del CSV
python diagnosticar_csv.py usuarios_bulk.csv
```

## Estructura del Proyecto

```
App1M-pg/
├── .env                    # Variables de entorno (no subir a Git)
├── .env.example            # Plantilla de variables de entorno
├── .gitignore              # Archivos excluidos de Git
├── requirements.txt        # Dependencias de Python
├── insertar_csv_copy.py    # Script principal (COPY)
├── insertar_csv_execute_values.py  # Script alternativo
├── insertar_csv_bulk.py    # Script SQL puro
├── diagnosticar_csv.py     # Diagnóstico de CSV
└── venv/                   # Entorno virtual (no subir a Git)
```

## Formato del CSV

El archivo CSV debe contener las siguientes columnas:

```csv
username,email,firstName,lastName,address,phoneNumber,active,role
usuario1,usuario1@email.com,John,Doe,"123 Main St",555-0101,true,guest
```

## Rendimiento Esperado

| Registros | COPY | execute_values | SQL puro |
|-----------|------|----------------|----------|
| 100K | ~2-5s | ~5-10s | ~10-20s |
| 1M | ~5-15s | ~10-20s | ~20-40s |
| 10M | ~50-150s | ~100-200s | ~200-400s |

## Solución de Problemas

### Error: `psycopg2.OperationalError`
- Verifica que PostgreSQL esté ejecutándose
- Confirma los datos de conexión en `.env`
- Verifica que la base de datos exista

### Error: `column does not exist`
- Ejecuta `diagnosticar_csv.py` para verificar la estructura del CSV
- Ajusta las columnas en el script según tu esquema

### Error: `duplicate key value`
- Los scripts manejan duplicados con `ON CONFLICT`
- Verifica que las columnas UNIQUE coincidan con tu CSV

## Licencia

MIT License
