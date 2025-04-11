# Asistente Inteligente RAG con Ollama

Este proyecto implementa un asistente inteligente basado en RAG (Retrieval-Augmented Generation) utilizando LangChain, Ollama y DuckDB.

## Requisitos Previos

1. Python 3.8 o superior
2. macOS (compatible con Ollama)
3. Ollama instalado y ejecutándose localmente
4. Modelo Llama3 descargado en Ollama

## Instalación

1. Clonar el repositorio:
```bash
git clone [url-del-repositorio]
cd [nombre-del-directorio]
```

2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Instalar Ollama en macOS:
```bash
# Instalar usando Homebrew
brew install ollama

# O descargar directamente desde el sitio web
# https://ollama.ai/download
```

5. Iniciar el servidor de Ollama:
```bash
# Iniciar el servicio
ollama serve

# Verificar que el servicio está corriendo
ollama list
```

6. Descargar el modelo Llama3:
```bash
# Descargar el modelo
ollama pull llama3

# Verificar que el modelo está disponible
ollama list
```

## Estructura del Proyecto

```
.
├── app.py              # Aplicación principal Streamlit
├── requirements.txt    # Dependencias del proyecto
├── data/              # Directorio para documentos
└── rag_db.duckdb      # Base de datos vectorial
```

## Uso

1. Asegúrate de que Ollama esté ejecutándose:
```bash
ollama serve
```

2. Iniciar la aplicación:
```bash
streamlit run app.py
```

3. En el navegador:
   - Subir un documento (.txt, .md o .csv)
   - Hacer preguntas sobre el contenido del documento
   - Recibir respuestas generadas por el modelo LLM con contexto del documento

## Comandos Útiles de Ollama

```bash
# Ver modelos disponibles
ollama list

# Eliminar un modelo
ollama rm llama3

# Ver información de un modelo
ollama show llama3

# Detener el servidor
pkill ollama
```

## Características

- Procesamiento de documentos en tiempo real
- Generación de embeddings con Ollama
- Almacenamiento vectorial con DuckDB
- Interfaz amigable con Streamlit
- Respuestas contextuales basadas en RAG

## Notas Importantes

- Asegúrate de tener suficiente memoria RAM para ejecutar el modelo Llama3 (recomendado mínimo 16GB)
- Los documentos grandes pueden tardar más en procesarse
- La primera ejecución puede ser más lenta debido a la inicialización de los modelos
- En macOS, asegúrate de que Ollama tenga los permisos necesarios en Preferencias del Sistema > Seguridad y Privacidad

## Solución de Problemas

Si encuentras problemas con Ollama en macOS:

1. Verifica que el servicio esté corriendo:
```bash
ps aux | grep ollama
```

2. Revisa los logs:
```bash
tail -f ~/.ollama/logs/server.log
```

3. Reinicia el servicio:
```bash
pkill ollama
ollama serve
```

## Licencia

MIT 