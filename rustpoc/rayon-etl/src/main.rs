// src/etl_rayon.rs
use csv::Reader;
use rayon::prelude::*;
use rusqlite::{Connection, params};
use std::error::Error;
use std::path::PathBuf;
use dashmap::DashMap;

fn main() -> Result<(), Box<dyn Error>> {
    // Extract & Transform
    let mut csv_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    csv_path.push("../empleados.csv");
    let reader = Reader::from_path(csv_path)?;
    
    let records: Vec<_> = reader
        .into_records()
        .par_bridge()  // Convertir a iterador paralelo
        .filter_map(|record| {
            let record = record.ok()?;
            let depto = record.get(3)?;
            let salary = record.get(2)?
                .parse::<f64>()
                .ok()?;
            Some((depto.to_string(), salary))
        })
        .collect();

    // Optimización 2: Usar HashMap concurrente
    let (departamentos, contador) = (DashMap::new(), DashMap::new());

    records.par_iter().for_each(|(depto, salario)| {
        departamentos.entry(depto.clone())
            .and_modify(|e| *e += salario)
            .or_insert(*salario);
        contador.entry(depto.clone())
            .and_modify(|c| *c += 1)
            .or_insert(1);
    });

    // Post-procesamiento eficiente
    let resultados: Vec<_> = departamentos
        .into_iter()
        .map(|(k, total)| {
            let count = *contador.get(&k).unwrap().value();
            (k, total / count as f64)
        })
        .collect();

    // Añadir escritura CSV
    let mut wtr = csv::Writer::from_path("salarios_promedio_rayon.csv")?;
    wtr.write_record(&["departamento", "promedio"])?;

    for (depto, promedio) in &resultados {
        wtr.write_record(&[
            depto, 
            &format!("{:.2}", promedio)
        ])?;
    }
    wtr.flush()?;

    // Mantener escritura SQLite existente
    let conn = Connection::open("empleados_rust.db")?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS salarios_promedio (departamento TEXT, promedio REAL)",
        [],
    )?;

    let mut stmt = conn.prepare("INSERT INTO salarios_promedio VALUES (?1, ?2)")?;
    for (depto, promedio) in resultados {
        stmt.execute(params![depto, promedio])?;
    }

    Ok(())
}