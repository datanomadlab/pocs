# Asistente Conversacional de Datos con Modelo Local DeepSeek

## Descripción

Este proyecto es un prototipo que permite a los usuarios transformar preguntas en lenguaje natural en consultas SQL, utilizando un modelo local especializado en generación de SQL basado en DeepSeek. El asistente procesa las preguntas y, mediante un pipeline optimizado, genera consultas que se pueden ejecutar sobre una base de datos local (por ejemplo, DuckDB).

## Características

- **Modelo local DeepSeek:** Uso del modelo `deepseek-ai/deepseek-coder-1.3b-instruct` descargado localmente.
- **Conversión de lenguaje natural a SQL:** Transformación automática de preguntas a consultas SQL.
- **Interfaz de usuario:** Aplicación web construida con Streamlit.
- **Validación y ejecución de consultas:** Solo se permiten consultas seguras (por ejemplo, aquellas que comienzan con `SELECT`).

## Requisitos

- Python 3.9+
- [Transformers](https://github.com/huggingface/transformers)
- [Torch](https://pytorch.org/)
- [Streamlit](https://streamlit.io/)
- Otras dependencias en `requirements.txt` (por ejemplo, sentencepiece si fuera necesario)

## Instalación

1. **Clonar el repositorio:**

   ```bash
   git clone https://github.com/tu_usuario/asistente-conversacional-datos.git
   cd asistente-conversacional-datos
   ```

2. **Crear y activar el entorno virtual:**

   ```bash
   python -m venv env
   source env/bin/activate   # Linux/Mac
   env\Scripts\activate      # Windows
   ```

3. **Instalar las dependencias:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Descargar el modelo DeepSeek:**

   - Descarga el modelo `deepseek-ai/deepseek-coder-1.3b-instruct` desde HuggingFace.
   - Coloca los archivos del modelo en la carpeta `./modelos` (o ajusta `MODEL_NAME` en `modules/llm_interface.py` a la ruta correcta).

5. **Inicializar la base de datos de ejemplo (si aplica):**

   Ejecuta el script de inicialización para cargar datos de prueba en DuckDB:

   ```bash
   python scripts/initialize_db.py
   ```

## Ejecución de la aplicación

Para ejecutar la aplicación con Streamlit, usa:

```bash
streamlit run app/app.py
```

Accede a la URL local que muestra Streamlit (por ejemplo, `http://localhost:8501`).

## Estructura del Proyecto

```
asistente-conversacional-datos/
├── app/
│   └── app.py                # Interfaz de usuario (Streamlit)
├── modules/
│   ├── __init__.py           # Archivo vacío para marcar el paquete
│   ├── llm_interface.py      # Conversión de lenguaje natural a SQL usando DeepSeek
│   ├── database.py           # Conexión y ejecución de consultas en DuckDB
│   └── validator.py          # Validación de consultas SQL
├── scripts/
│   └── initialize_db.py      # Script para poblar la base de datos de ejemplo
├── modelos/                  # Carpeta donde se almacena el modelo DeepSeek descargado
├── config.py                 # Configuraciones (por ejemplo, ruta a la base de datos)
├── requirements.txt          # Dependencias del proyecto
└── README.md                 # Este archivo
```

## Notas

- **Modelo Local:** El modelo se carga desde archivos locales usando `local_files_only=True` y `trust_remote_code=True`. Asegúrate de haber descargado correctamente el modelo.
- **Optimización:** Se utiliza `torch_dtype=torch.float16` para reducir el uso de memoria. Puedes ajustar este parámetro según tus necesidades.
- **Seguridad:** Solo se permiten consultas que comiencen con `SELECT` para evitar operaciones destructivas en la base de datos.
