# modules/validator.py
from config import ALLOWED_SQL_PREFIXES
import re
import duckdb


def validar_query(query: str) -> bool:
    """Valida consultas SQL de forma más flexible en inglés"""
    clean_query = re.sub(r'--.*', '', query)
    clean_query = re.sub(r'/\*.*?\*/', '', clean_query, flags=re.DOTALL)
    q = clean_query.lower().strip()
    
    # Extraer solo la parte SELECT
    select_part = q.split("from")[0] if "from" in q else q
    
    # Lista de elementos permitidos
    allowed_elements = {
        'functions': ["avg", "sum", "count", "max", "min"],
        'columns': ["id", "product", "quantity", "saledate"],
        'keywords': ["select", "from", "where", "group by", "order by", "as"]
    }
    
    # Verificar estructura básica
    if not q.startswith("select") or "from sales" not in q:
        return False
    
    # Verificar palabras prohibidas
    if any(bad_word in q for bad_word in ["drop", "insert", "update", "delete", "alter", "create", "replace"]):
        return False
    
    # Validar elementos del SELECT
    select_items = select_part.replace("select", "").split(",")
    for item in select_items:
        item = item.strip()
        
        # Verificar si es una función
        if "(" in item:
            func = item.split("(")[0].strip()
            if func not in allowed_elements['functions']:
                return False
            
            # Verificar columna dentro de la función
            col = item.split("(")[1].split(")")[0].strip()
            if col not in allowed_elements['columns']:
                return False
            
        # Verificar si es columna con alias
        elif " as " in item:
            col, alias = item.split(" as ", 1)
            col = col.strip()
            alias = alias.strip()
            
            if col not in allowed_elements['columns']:
                return False
            if not alias.replace("_", "").isalnum():
                return False
            
        # Verificar columna simple
        else:
            if item not in allowed_elements['columns']:
                return False
                
    return True

con = duckdb.connect("my_database.duckdb")
print(con.execute("DESCRIBE sales").fetchdf())
