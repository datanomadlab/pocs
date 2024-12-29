from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp
import os

class PostgresToMySQLETL:
    def __init__(self, postgres_config, mysql_config):
        self.postgres_config = postgres_config
        self.mysql_config = mysql_config

        # Configurar variables de entorno antes de crear SparkSession
        os.environ['SPARK_LOCAL_IP'] = 'localhost'
        os.environ['HADOOP_HOME'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.environ['JAVA_HOME'] = '/opt/homebrew/opt/openjdk@17'  # Ajusta esta ruta según tu instalación
        
        # Obtener la ruta absoluta de los conectores
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        postgres_jar = os.path.join(base_path, "utils", "postgresql-connector.jar")
        mysql_jar = os.path.join(base_path, "utils", "mysql-connector.jar")
        jar_path = f"{postgres_jar},{mysql_jar}"

        # Crear la sesión de Spark con configuraciones adicionales
        self.spark = SparkSession.builder \
            .appName("PostgresToMySQL_ETL") \
            .config("spark.jars", jar_path) \
            .config("spark.driver.extraJavaOptions", "-Dcom.sun.security.auth.module.UnixLoginModule") \
            .config("spark.executor.extraJavaOptions", "-Dcom.sun.security.auth.module.UnixLoginModule") \
            .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
            .config("spark.driver.host", "localhost") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .config("spark.security.credentials.hadoopfs.enabled", "false") \
            .master("local[*]") \
            .getOrCreate()

    def extract(self, table_name):
        """
        Extrae datos de una tabla en PostgreSQL usando PySpark.
        """
        jdbc_url = f"jdbc:postgresql://{self.postgres_config['host']}:{self.postgres_config['port']}/{self.postgres_config['dbname']}"
        properties = {
            "user": self.postgres_config["user"],
            "password": self.postgres_config["password"],
            "driver": "org.postgresql.Driver"
        }

        print(f"Extrayendo datos de la tabla {table_name}...")
        df = self.spark.read.jdbc(url=jdbc_url, table=table_name, properties=properties)
        return df

    def transform(self, df):
        """
        Aplica transformaciones a los datos.
        """
        print("Transformando datos...")
        # Limpieza de datos nulos
        df = df.na.fill({"address": "Unknown"})
        
        # Deduplicación
        df = df.dropDuplicates(["email"])
        
        # Normalización de texto y añadir processed_date
        df = df.select(
            "id",
            col("name").alias("name"),
            "email",
            "address"
        ).withColumn("processed_date", current_timestamp())
        
        return df

    def load(self, df, table_name):
        """
        Carga los datos transformados en una tabla MySQL.
        """
        # Seleccionar solo las columnas necesarias en el orden correcto
        columns_to_load = ["id", "name", "email", "address", "processed_date"]
        df_to_load = df.select(*columns_to_load)

        jdbc_url = f"jdbc:mysql://{self.mysql_config['host']}:{self.mysql_config['port']}/{self.mysql_config['dbname']}"
        properties = {
            "user": self.mysql_config["user"],
            "password": self.mysql_config["password"],
            "driver": "com.mysql.cj.jdbc.Driver"
        }

        print(f"Cargando datos en la tabla {table_name}...")
        df_to_load.write.jdbc(url=jdbc_url, table=table_name, mode="append", properties=properties)

    def run_etl(self, source_table, target_table):
        """
        Ejecuta el flujo completo de ETL.
        """
        df = self.extract(source_table)
        transformed_df = self.transform(df)
        self.load(transformed_df, target_table)

if __name__ == "__main__":
    # Configuraciones para PostgreSQL y MySQL
    postgres_config = {
        "host": "localhost",
        "port": 5432,
        "dbname": "test_db",
        "user": "test_user",
        "password": "test_password"
    }
    
    mysql_config = {
        "host": "localhost",
        "port": 3306,
        "dbname": "test_db",
        "user": "test_user",
        "password": "test_password"
    }
    
    etl = PostgresToMySQLETL(postgres_config, mysql_config)
    etl.run_etl("records", "transformed_records")
