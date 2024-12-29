import csv
from faker import Faker
from datetime import datetime

def generate_csv(file_path, num_records):
    """
    Genera un archivo CSV con un esquema consistente con la tabla PostgreSQL.
    """
    fake = Faker()
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Escribir encabezados
        writer.writerow(["id", "name", "email", "address", "created_at", "updated_at"])
        
        for i in range(1, num_records + 1):
            # Generar datos ficticios
            name = fake.name()
            email = fake.email()
            address = fake.address().replace("\n", ", ")
            created_at = fake.date_time_this_decade().strftime('%Y-%m-%d %H:%M:%S')
            updated_at = fake.date_time_this_year().strftime('%Y-%m-%d %H:%M:%S')
            # Escribir registro
            writer.writerow([i, name, email, address, created_at, updated_at])

if __name__ == "__main__":
    output_file = "src/data/sample_data.csv"  # Ruta del archivo CSV
    num_records = 1000  # Cambia este valor según lo que necesites
    generate_csv(output_file, num_records)
    print(f"Archivo CSV generado en: {output_file}")
