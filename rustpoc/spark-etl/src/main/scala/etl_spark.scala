// etl_spark.scala
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._

object SparkETL {
  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder
      .appName("ETL-Spark")
      .master("local[*]")
      .getOrCreate()

    // Configuración para SQLite
    val sqliteOptions = Map(
      "url" -> "jdbc:sqlite:empleados_spark.db",
      "dbtable" -> "salarios_promedio"
    )

    // Extract y Transform
    val df = spark.read
      .option("header", "true")
      .csv("empleados.csv")
      .filter(col("salario").rlike("^\\d+$"))
      .withColumn("salario", col("salario").cast("double"))

    // Agregación
    val avgDF = df.groupBy("departamento")
      .agg(avg("salario").alias("promedio"))

    // Agregar configuración explícita de logging
    spark.sparkContext.setLogLevel("WARN")

    // Especificar formato de escritura para CSV
    avgDF.write
      .format("csv")
      .option("header", "true")
      .save("salarios_promedio_spark")

    // Load
    avgDF.write.format("jdbc")
      .options(sqliteOptions)
      .mode("overwrite")
      .save()

    spark.stop()
  }
}