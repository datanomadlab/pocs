from config import INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET
from influxdb_client import InfluxDBClient, Point

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

write_api = client.write_api()


def write_to_influxdb(event):
    point = (
        Point("pos_data")
        .tag("store_id", event["store_id"])
        .tag("pos_id", event["pos_id"])
        .time(event["timestamp"])
        .field("total_sales", event["total_sales"])
        .field("items_sold", event["items_sold"])
        .field("transaction_count", event["transaction_count"])
    )
    write_api.write(bucket=INFLUXDB_BUCKET, record=point)
