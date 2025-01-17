import pyarrow as pa
import pyarrow.compute as pc

# Crear dos tablas Arrow
data1 = {
    "id": [1, 2, 3],
    "value": [100, 200, 300]
}
table1 = pa.table(data1)

data2 = {
    "id": [2, 3, 4],
    "name": ["Alice", "Bob", "Charlie"]
}
table2 = pa.table(data2)

# Realizar un join entre las dos tablas
join_condition = pc.equal(table1["id"], table2["id"])
result_table = pa.Table.from_arrays(
    [
        table1["id"].filter(join_condition),
        table1["value"].filter(join_condition),
        table2["name"].filter(join_condition)
    ],
    names=["id", "value", "name"]
)

print("Resultado del Join:")
print(result_table)