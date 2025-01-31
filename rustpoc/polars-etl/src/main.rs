use std::time::Instant;
use polars::prelude::*;
use sysinfo::{System, Pid};

// Función para obtener la memoria usada (en KB)
fn get_memory_usage() -> u64 {
    let mut sys = System::new_all();
    sys.refresh_all();
    // Convierte el ID del proceso (u32) a usize para construir el Pid
    let pid = Pid::from(std::process::id() as usize);
    if let Some(process) = sys.process(pid) {
        process.memory() // Retorna la memoria en KB
    } else {
        0
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let start = Instant::now();

    let csv_path = "empleados.csv"; // Se asume que el CSV está en el directorio actual
    println!("Buscando CSV en: {}", csv_path);

    let df = CsvReader::from_path(csv_path)?
        .has_header(true)
        .finish()?;

    // Agrupamos por "departamento" y calculamos el promedio de "salario" usando el método mean()
    let mut avg_df = df.group_by(["departamento"])?.mean()?;
    // El resultado de .mean() genera la columna "salario_mean"; la renombramos a "promedio"
    avg_df.rename("salario_mean", "promedio")?;

    let mem_kb = get_memory_usage();
    let mem_mb = mem_kb as f64 / (1024.0 * 1024.0);  // Convertir de bytes a MB
    let elapsed = start.elapsed().as_secs_f64();
    println!("Tiempo: {:.2}s, Memoria: {:.2}MB", elapsed, mem_mb);

    Ok(())
}