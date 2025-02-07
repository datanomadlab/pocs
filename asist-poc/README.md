# Asistente Conversacional de Datos con Modelo Local DeepSeek y DuckDB

## Descripción

Este proyecto es un prototipo que permite transformar preguntas en lenguaje natural en consultas SQL utilizando un modelo local especializado en SQL (DeepSeek) y ejecutándolas en una base de datos local (DuckDB). La solución está diseñada para entornos de prototipado, ofreciendo rapidez, seguridad y facilidad de uso.

## Características

- **Modelo Local DeepSeek:** Utiliza el modelo `deepseek-ai/deepseek-coder-1.3b-instruct` para generar consultas SQL de alta precisión.
- **DuckDB:** Base de datos embebida para ejecutar consultas analíticas de manera local, sin necesidad de servidores externos.
- **Validación de Consultas:** Se implementan validadores para asegurar que las consultas generadas sean seguras, correctas y adaptadas a la estructura de la tabla `sales`.
- **Interfaz de Usuario:** Aplicación web desarrollada con Streamlit para facilitar la interacción y visualización de resultados.

## Ventajas de la Solución

### DuckDB
- **Ligereza y Portabilidad:** Al ser embebido, no requiere configuraciones complejas.
- **Alto Rendimiento:** Ideal para consultas analíticas en entornos de prueba y desarrollo.
- **Fácil Integración:** Permite trabajar con archivos locales, simplificando el despliegue.

### DeepSeek
- **Especializado en SQL:** Entrenado para generar consultas SQL de calidad a partir de instrucciones en inglés.
- **Ejecución Local:** Reduce la dependencia de APIs externas, mejorando la privacidad y latencia.
- **Optimización de Recursos:** Configurable con `torch_dtype` para adaptarse a distintas capacidades de hardware.

### Validadores
- **Seguridad:** Previenen la ejecución de consultas destructivas, limitando operaciones a lecturas (por ejemplo, evitando `DROP`, `DELETE`, etc.).
- **Integridad de Datos:** Aseguran que las consultas se ajusten a la estructura de la tabla `sales` y usen columnas y funciones permitidas.
- **Consistencia:** Garantizan que, ante consultas incompletas o erróneas, se retorne un fallback (consulta por defecto) para mantener la experiencia del usuario.

## Requisitos

- Python 3.9+
- [Transformers](https://github.com/huggingface/transformers)
- [Torch](https://pytorch.org/)
- [Streamlit](https://streamlit.io/)
- [DuckDB](https://duckdb.org/)
- Dependencias adicionales listadas en `requirements.txt` (ej. `sentencepiece`, etc.)

## Instalación

0. **Instalar modelo DeepSeek:**
   ```bash
   huggingface-cli download deepseek-ai/deepseek-coder-1.3b-instruct --local-dir ./modelos --local-dir-use-symlinks False
   ```

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/tu_usuario/asistente-conversacional-datos.git
   cd asistente-conversacional-datos
   ```

2. **Crear y activar entorno virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate # Linux/Mac
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación:**
   ```bash
   streamlit run app/app.py
   ```

