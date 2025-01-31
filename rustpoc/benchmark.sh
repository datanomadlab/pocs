#!/bin/bash

# Configurar directorio base
BASE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$BASE_DIR"  # Cambiar al directorio raíz donde está el CSV

echo "=== BENCHMARK DE PERFORMANCE ==="

# Compilar proyectos
echo "Compilando..."
cargo build --release

run_benchmark() {
    local name=$1
    local cmd=$2
    echo -e "\nEjecutando $name..."
    
    cd "$BASE_DIR"  # Asegurar que estamos en el directorio correcto para cada ejecución
    start_time=$(date +%s)
    $cmd
    end_time=$(date +%s)
    
    elapsed=$((end_time - start_time))
    echo "Tiempo: ${elapsed}s"
}

# Ejecutar benchmarks
run_benchmark "Generate Data" "python3 generate_data.py"
run_benchmark "Rust Polars" "./target/release/polars-etl"
run_benchmark "Rust Rayon" "./target/release/rayon-etl"
run_benchmark "Python Pandas" "python3 etl_pandas.py"

echo -e "\n=== RESULTADOS FINALES ==="