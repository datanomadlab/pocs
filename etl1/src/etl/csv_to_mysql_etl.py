from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp

class CSVToMySQLETL:
    def __init__(self, mysql_config, csv_file_path):
        self.mysql_config = mysql_config
        self.csv_file_path = csv_file_path

        # Crear la sesión de Spark
        self.spark = SparkSession.builder \
            .appName("CSVToMySQL_ETL") \
            .config("spark.jars", "src/utils/mysql-connector.jar") \
            .getOrCreate()

    def extract(self):
        """
        Lee datos desde un archivo CSV.
        """
        print(f"Leyendo datos desde el archivo: {self.csv_file_path}...")
        df = self.spark.read.csv(self.csv_file_path, header=True, inferSchema=True)
        return df

    def transform(self, df):
        """
        Aplica transformaciones a los datos.
        """
        print("Transformando datos...")
        # Limpieza de datos nulos
        df = df.na.fill({"address": "Unknown"})

        # Añadir columna de fecha de procesamiento
        df = df.select(
            "id",
            "name",
            "email",
            "address"
        ).withColumn("processed_date", current_timestamp())

        return df

    def load(self, df, table_name):
        """
        Carga los datos transformados en una tabla MySQL.
        """
        # Asegurarse de que solo se cargan las columnas necesarias en el orden correcto
        columns_to_load = ["id", "name", "email", "address", "processed_date"]
        df_to_load = df.select(*columns_to_load)

        jdbc_url = f"jdbc:mysql://{self.mysql_config['host']}:{self.mysql_config['port']}/{self.mysql_config['dbname']}"
        properties = {
            "user": self.mysql_config["user"],
            "password": self.mysql_config["password"],
            "driver": "com.mysql.cj.jdbc.Driver"
        }

        print(f"Cargando datos en la tabla {table_name}...")
        
        df_to_load.write.jdbc(
            url=jdbc_url, 
            table=table_name, 
            mode="overwrite",
            properties=properties
        )

    def run_etl(self, target_table):
        """
        Ejecuta el flujo completo de ETL.
        """
        df = self.extract()
        transformed_df = self.transform(df)
        self.load(transformed_df, target_table)

if __name__ == "__main__":
    # Configuración de MySQL
    mysql_config = {
        "host": "localhost",
        "port": 3306,
        "dbname": "test_db",
        "user": "test_user",
        "password": "test_password"
    }
    
    # Ruta del archivo CSV
    csv_file_path = "src/data/sample_data.csv"  # Actualiza con la ruta real del CSV

    etl = CSVToMySQLETL(mysql_config, csv_file_path)
    etl.run_etl("transformed_records")
