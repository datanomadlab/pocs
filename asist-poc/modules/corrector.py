import re

def corregir_consulta(query: str, pregunta: str) -> str:
    """Corrige y valida la consulta SQL."""
    # Asegurar que tenemos una consulta básica válida
    if not query or not query.lower().strip().startswith("select"):
        return ""
    
    # Limpiar la consulta
    query = ' '.join(query.split()).strip()
    
    # Asegurar que tenemos FROM sales
    if "from sales" not in query.lower():
        parts = query.split("FROM")
        if len(parts) == 1:
            query = f"{parts[0]} FROM sales"
        
    # Asegurar ORDER BY para consultas de ventas recientes
    if any(word in query.lower() for word in ['recent', 'latest', 'new', 'last']):
        if "order by" not in query.lower():
            query += " ORDER BY saledate DESC"
        if "limit" not in query.lower():
            query += " LIMIT 1"
            
    # Asegurar punto y coma al final
    if not query.endswith(";"):
        query += ";"
        
    # Manejar consultas de productos más vendidos
    if any(keyword in pregunta.lower() for keyword in ['most sold', 'most selled', 'highest sales']):
        if 'count(' not in query.lower():
            query = re.sub(r'SUM\(quantity\)', 'COUNT(*)', query, flags=re.IGNORECASE)
        if 'order by' not in query.lower():
            query += ' ORDER BY order_count DESC LIMIT 1'
        elif 'order by' in query.lower() and 'limit' not in query.lower():
            query += ' LIMIT 1'
        
    elif any(keyword in query.lower() for keyword in ['most frequent', 'most ordered', 'most common']):
        if 'count(' not in query.lower():
            query = re.sub(r'SUM\(quantity\)', 'COUNT(*)', query, flags=re.IGNORECASE)
        if 'order by' not in query.lower():
            query += ' ORDER BY total_orders DESC'
        
    # También reemplazar cualquier referencia incorrecta en la consulta
    query = query.replace('sale_date', 'saledate')
        
    return query 