use polars::prelude::*;
use polars::sql::SQLContext;
use rusqlite::Connection;
use rusqlite::params;
use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Obtener ruta absoluta del CSV
    let mut csv_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    csv_path.push("../empleados.csv");  // Solo subir 1 nivel
    
    println!("Buscando CSV en: {}", csv_path.display());
    
    // Extract
    let df = LazyCsvReader::new(csv_path)
        .has_header(true)
        .finish()?
        .filter(col("salario").str().to_decimal(2).cast(DataType::Float64).is_not_null())
        .select(&[
            col("departamento"),
            col("salario").str().to_decimal(2).cast(DataType::Float64).alias("salario")
        ])
        .cache()
        .with_streaming(true);

    // Transform
    let avg_df = df
        .group_by(["departamento"])
        .agg([col("salario").mean().alias("promedio")])
        .collect()?;

    // Clonar antes de mover
    let avg_df_for_sql = avg_df.clone();

    // Registrar el clon en el contexto SQL
    let mut ctx = SQLContext::new();
    ctx.register("data", avg_df_for_sql.lazy());
    
    // Ejecutar consulta SQL
    let sql_query = r#"
        CREATE TABLE salarios_promedio AS
        SELECT departamento, promedio FROM data
    "#;
    let _result = ctx.execute(sql_query)?.collect()?;
    
    // Mantener ambas escrituras
    let mut file = std::fs::File::create("salarios_promedio_polars.csv")?;
    CsvWriter::new(&mut file)
        .include_header(true)
        .finish(&mut avg_df.clone())?;

    // Escribir a SQLite
    let conn = Connection::open("empleados.db")?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS salarios_promedio (
            departamento TEXT, 
            promedio REAL
        )", 
        []
    )?;

    let mut stmt = conn.prepare(
        "INSERT INTO salarios_promedio VALUES (?, ?)"
    )?;

    for row in 0..avg_df.height() {
        let depto = avg_df.column("departamento")?.str()?.get(row).ok_or_else(|| {
            PolarsError::ComputeError("Departamento inválido".into())
        })?;
        let prom = avg_df.column("promedio")?.f64()?.get(row).ok_or_else(|| {
            PolarsError::ComputeError("Promedio inválido".into())
        })?;
        stmt.execute(params![depto, prom as f64])?;
    }
    
    Ok(())
}