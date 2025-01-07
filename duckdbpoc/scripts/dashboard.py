import streamlit as st
import duckdb
import pandas as pd
import matplotlib.pyplot as plt

# Configuración
INPUT_FILE = "./data/inputpoc1.parquet"

# Función para cargar datos con DuckDB
@st.cache_data
def load_data(input_file):
    conn = duckdb.connect()
    query = f"SELECT * FROM read_parquet('{input_file}')"
    return conn.execute(query).fetchdf()

# Función para filtrar y analizar datos
def filter_and_analyze_data(df, category, date_range):
    # Convertir date_range a datetime64
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    
    filtered_data = df[(df['category'] == category) & 
                       (df['timestamp'] >= start_date) & 
                       (df['timestamp'] <= end_date)]
    
    summary = filtered_data.groupby("category").agg(
        total_value=pd.NamedAgg(column="value", aggfunc="sum"),
        avg_value=pd.NamedAgg(column="value", aggfunc="mean"),
        count=pd.NamedAgg(column="value", aggfunc="count")
    ).reset_index()
    return filtered_data, summary

# Cargar datos
st.title("Dashboard Interactivo con Streamlit y DuckDB")
st.sidebar.header("Filtros")
data = load_data(INPUT_FILE)

# Filtros
category = st.sidebar.selectbox("Selecciona Categoría", data["category"].unique())
date_range = st.sidebar.date_input(
    "Rango de Fechas", 
    [data["timestamp"].min(), data["timestamp"].max()]
)

# Filtrar y analizar datos
filtered_data, summary = filter_and_analyze_data(data, category, date_range)

# Mostrar datos filtrados
st.subheader("Datos Filtrados")
st.dataframe(filtered_data)

# Mostrar resumen
st.subheader("Resumen de Análisis")
st.table(summary)

# Gráficos
st.subheader("Gráficos")
fig, ax = plt.subplots()
ax.bar(filtered_data["timestamp"], filtered_data["value"])
ax.set_title(f"Valores por Fecha - Categoría {category}")
ax.set_xlabel("Fecha")
ax.set_ylabel("Valor")
st.pyplot(fig)
