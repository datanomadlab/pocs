import psycopg2
from faker import Faker
import random

class DataGenerator:
    def __init__(self, db_config):
        self.connection = psycopg2.connect(**db_config)
        self.cursor = self.connection.cursor()
        self.fake = Faker()

    def generate_data(self, num_records):
        for _ in range(num_records):
            name = self.fake.name()
            email = self.fake.email()
            address = self.fake.address().replace('\n', ', ')
            created_at = self.fake.date_time_this_decade()
            updated_at = self.fake.date_time_this_year()

            yield (name, email, address, created_at, updated_at)

    def populate_database(self, num_records):
        insert_query = """
        INSERT INTO records (name, email, address, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s);
        """
        batch_size = 10000
        data = self.generate_data(num_records)
        
        for batch in self._batch_data(data, batch_size):
            self.cursor.executemany(insert_query, batch)
            self.connection.commit()
            print(f"Inserted {len(batch)} records")

    def _batch_data(self, data, batch_size):
        batch = []
        for record in data:
            batch.append(record)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def close_connection(self):
        self.cursor.close()
        self.connection.close()

if __name__ == "__main__":
    db_config = {
        "dbname": "test_db",
        "user": "test_user",
        "password": "test_password",
        "host": "localhost",
        "port": 5432,
    }

    generator = DataGenerator(db_config)
    try:
        generator.populate_database(10000000)  # 10 millones de registros
    finally:
        generator.close_connection()
