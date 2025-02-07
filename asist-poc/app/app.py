import sys
import os
import re

# Agregar el directorio raíz al sys.path (debe hacerse antes de importar módulos personalizados)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from modules.llm_interface import generar_sql
from modules.database import ejecutar_query
from modules.validator import validar_query
from modules.corrector import corregir_consulta

st.title("Asistente Conversacional de Datos - Modelo Local")

st.markdown(
    """
    **Nota:** El modelo de generación de SQL está entrenado en inglés.
    Ejemplos de preguntas efectivas:
    - "Show me the product with highest total quantity sold"
    - "Which product appears most frequently in orders?"
    - "List products by number of sales"
    """
)

pregunta = st.text_input("Ingresa tu pregunta (en inglés):")

if st.button("Generar consulta y ejecutar"):
    if pregunta:
        st.write("Generando consulta SQL...")
        query = generar_sql(pregunta)
        query = corregir_consulta(query, pregunta)
        st.code(query, language='sql')
        
        if validar_query(query):
            st.write("Ejecutando consulta...")
            try:
                resultados = ejecutar_query(query)
                st.write("Resultados:")
                st.table(resultados)
            except Exception as e:
                st.error(f"Error al ejecutar la consulta: {e}")
        else:
            st.error("La consulta generada no es válida o segura.")
    else:
        st.warning("Por favor, ingresa una pregunta.")

