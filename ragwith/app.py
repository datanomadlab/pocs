import streamlit as st
from langchain_ollama import OllamaLLM
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import DuckDB
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
import duckdb
import os
from dotenv import load_dotenv
import pandas as pd
from pathlib import Path

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="Asistente RAG con Ollama",
    page_icon="🤖",
    layout="wide"
)

# Título de la aplicación
st.title("🤖 Asistente Inteligente RAG")
st.markdown("""
Este asistente utiliza RAG (Retrieval-Augmented Generation) para responder preguntas basadas en documentos.
""")

# Inicialización de componentes
@st.cache_resource
def init_components():
    # Inicializar el modelo LLM
    llm = OllamaLLM(model="llama3")
    
    # Inicializar embeddings
    embeddings = OllamaEmbeddings(model="llama3")
    
    # Inicializar DuckDB
    conn = duckdb.connect('rag_db.duckdb')
    
    # Crear tabla para documentos si no existe
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS doc_id_seq;
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY DEFAULT nextval('doc_id_seq'),
            filename TEXT,
            content TEXT,
            processed_at TIMESTAMP
        )
    """)
    
    return llm, embeddings, conn

# Función para cargar y procesar documentos
def process_document(file, embeddings, conn):
    # Leer el contenido del archivo
    content = file.getvalue().decode("utf-8")
    filename = file.name
    
    # Verificar si el documento ya existe
    existing_doc = conn.execute("""
        SELECT id FROM documents WHERE filename = ?
    """, [filename]).fetchone()
    
    if existing_doc:
        st.warning(f"El documento {filename} ya ha sido procesado anteriormente.")
        return None
    
    # Dividir el texto en chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_text(content)
    
    # Crear vector store
    vector_store = DuckDB.from_texts(
        texts=chunks,
        embedding=embeddings,
        connection=conn
    )
    
    # Guardar metadatos del documento
    conn.execute("""
        INSERT INTO documents (filename, content, processed_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, [filename, content])
    
    return vector_store

# Función para cargar documentos existentes
def load_existing_documents(embeddings, conn):
    # Obtener todos los documentos procesados
    docs = conn.execute("""
        SELECT filename, content FROM documents
    """).fetchall()
    
    if not docs:
        return None
    
    # Procesar todos los documentos
    all_chunks = []
    for doc in docs:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_text(doc[1])
        all_chunks.extend(chunks)
    
    # Crear vector store con todos los documentos
    vector_store = DuckDB.from_texts(
        texts=all_chunks,
        embedding=embeddings,
        connection=conn
    )
    
    return vector_store

# Función principal
def main():
    llm, embeddings, conn = init_components()
    
    # Cargar documento
    st.sidebar.header("Cargar Documento")
    uploaded_file = st.sidebar.file_uploader(
        "Sube un archivo (.txt, .md, .csv)",
        type=['txt', 'md', 'csv']
    )
    
    # Cargar documentos existentes
    vector_store = load_existing_documents(embeddings, conn)
    
    if uploaded_file is not None:
        new_vector_store = process_document(uploaded_file, embeddings, conn)
        if new_vector_store:
            vector_store = new_vector_store
    
    if vector_store:
        # Crear cadena de QA
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vector_store.as_retriever()
        )
        
        # Interfaz de preguntas
        st.header("Haz una pregunta sobre los documentos")
        question = st.text_input("Tu pregunta:")
        
        if question:
            with st.spinner("Pensando..."):
                response = qa_chain.run(question)
                st.write("Respuesta:", response)
    else:
        st.info("No hay documentos cargados. Por favor, sube un documento para comenzar.")

if __name__ == "__main__":
    main() 