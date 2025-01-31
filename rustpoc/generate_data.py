import pandas as pd
import numpy as np

# Generar 10 millones de filas (~1GB)
num_rows = 10_000_000
departamentos = ['Ventas', 'IT', 'RH', 'Finanzas', 'Logística']

data = {
    'id': np.arange(num_rows),
    'nombre': ['Empleado_' + str(i) for i in range(num_rows)],
    'salario': np.random.normal(50000, 15000, num_rows).astype(int),
    'departamento': np.random.choice(departamentos, num_rows)
}

# Introducir un 5% de errores en salario
data['salario'] = np.where(np.random.rand(num_rows) < 0.05, 'invalid', data['salario'])

df = pd.DataFrame(data)
df.to_csv("empleados.csv", index=False)