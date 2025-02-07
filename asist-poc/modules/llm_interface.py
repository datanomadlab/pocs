# modules/llm_interface.py
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

# Modelo especializado en SQL (mejor que T5 para esta tarea)
MODEL_NAME = "./modelos"  # Usar modelo descargado localmente

# Cargar modelo y tokenizer con configuración óptima
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
    local_files_only=True  # Forzar uso local
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    trust_remote_code=True,
    local_files_only=True,
    torch_dtype=torch.float16  # Reduce uso de memoria
)

# Pipeline mejorado con parámetros para SQL
sql_pipeline = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=128,
    do_sample=False,  # Hacemos que sea determinista
    num_return_sequences=1
)

def generar_sql(pregunta: str) -> str:
    try:
        # Prompt simple y directo
        prompt = f"""### Sistema: Genera consultas SQL válidas usando la tabla 'sales' con las columnas: id, product, quantity, sale_date

        ### Ejemplo 1
        Pregunta: what's the most recent sale?
        SQL: SELECT id, product, quantity, saledate FROM sales ORDER BY saledate DESC LIMIT 1;

        ### Ejemplo 2
        Pregunta: what's the most sold product by quantity?
        SQL: SELECT product, SUM(quantity) as total_quantity FROM sales GROUP BY product ORDER BY total_quantity DESC;

        ### Ejemplo 3
        Pregunta: what's the most frequently ordered product?
        SQL: SELECT product, COUNT(*) as total_orders FROM sales GROUP BY product ORDER BY total_orders DESC;

        ### Ejemplo 4
        Pregunta: list products by sales frequency
        SQL: SELECT product, COUNT(*) as order_count FROM sales GROUP BY product ORDER BY order_count DESC;

        ### Ejemplo 5
        Pregunta: show total quantity per product
        SQL: SELECT product, SUM(quantity) as total_quantity FROM sales GROUP BY product ORDER BY total_quantity DESC;

        ### Ejemplo 6
        Pregunta: {pregunta}
        SQL: SELECT"""

        # Consulta por defecto para ventas más recientes
        default_query = """SELECT id, product, quantity, sale_date 
                          FROM sales 
                          ORDER BY sale_date DESC 
                          LIMIT 1;"""
  
        resultado = sql_pipeline(
            prompt,
            max_new_tokens=128,
            do_sample=False,
            num_beams=1,
            temperature=0.1
        )[0]['generated_text']
        
        # Extraer la consulta después del último "SQL: "
        try:
            query = resultado.split("SQL: ")[-1].split("###")[0].strip()
        except:
            query = ""
        
        # Validar que la consulta sea completa
        required_elements = ["select", "from", "sales"]
        if not all(elem in query.lower() for elem in required_elements):
            # Si la pregunta es sobre ventas recientes
            if any(word in pregunta.lower() for word in ['recent', 'latest', 'new', 'last']):
                return default_query
            else:
                query = default_query  # Usar consulta por defecto como fallback
        
        return query.strip() + ";" if not query.strip().endswith(";") else query.strip()
    
    except Exception as e:
        raise Exception(f"Error generación SQL: {str(e)[:200]}")
