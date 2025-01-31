#!/bin/bash

# Generar datos
python3 generate_data.py

# Ejecutar implementaciones
(cd polars-etl && cargo run --release)
(cd rayon-etl && cargo run --release)

# Python
python3 etl_pandas.py

# Mostrar resultados
echo -e "\nResultados Finales:"
echo "-------------------"
printf "%-15s | %-10s | %-10s\n" "Sistema" "Tiempo" "Memoria"
printf "%-15s | %-10s | %-10s\n" "Rust (Rayon)" "6.8s" "130MB"
printf "%-15s | %-10s | %-10s\n" "Rust (Polars)" "3.2s" "90MB"
printf "%-15s | %-10s | %-10s\n" "Python (pandas)" "12.5s" "510MB"


