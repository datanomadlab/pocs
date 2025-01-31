use std::error::Error;
use std::time::Instant;
use serde::Deserialize;
use dashmap::DashMap;
use rayon::iter::{IntoParallelRefIterator, ParallelIterator};
use rusqlite::{Connection, params};
use sysinfo::{System, Pid};

#[derive(Debug, Deserialize)]
struct Record {
    salario: f64,
    departamento: String,
}

// Función para obtener la memoria usada (en KB)
fn get_memory_usage() -> u64 {
    let mut sys = System::new_all();
    sys.refresh_all();
    let pid = Pid::from(std::process::id() as usize);
    if let Some(process) = sys.process(pid) {
        process.memory() // Retorna la memoria en KB
    } else {
        0
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    let start = Instant::now();

    let csv_path = "empleados.csv";  // Se asume que el CSV está en el directorio actual
    println!("Buscando CSV en: {}", csv_path);

    let mut reader = csv::Reader::from_path(csv_path)?;
    let records: Vec<Record> = reader.deserialize()
        .filter_map(Result::ok)
        .collect();

    // Procesamiento en paralelo: contar registros por departamento
    let departamentos: DashMap<String, u64> = DashMap::new();
    records.par_iter().for_each(|record| {
        departamentos.entry(record.departamento.clone())
            .and_modify(|count: &mut u64| { *count += 1 })
            .or_insert(1);
    });

    // Conexión a SQLite y creación de la tabla "departamentos" si no existe
    let conn = Connection::open("empleados_rust.db")?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS departamentos (
           nombre TEXT,
           contador INTEGER
         )",
         [],
    )?;

    // Inserción de cada departamento en la base de datos
    for entry in departamentos.iter() {
        let depto = entry.key();
        let count = *entry.value();
        conn.execute(
            "INSERT INTO departamentos (nombre, contador) VALUES (?1, ?2)",
            params![depto, count],
        )?;
    }

    let mem_kb = get_memory_usage();
    let mem_mb = mem_kb as f64 / (1024.0 * 1024.0);  // Convertir de bytes a MB
    let elapsed = start.elapsed().as_secs_f64();
    println!("Tiempo: {:.2}s, Memoria: {:.2}MB", elapsed, mem_mb);

    Ok(())
}