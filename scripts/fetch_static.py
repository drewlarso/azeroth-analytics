from bnet.client import (
    BlizzardClient,
    ItemData,
    ItemClassData,
    ItemSubclassData,
    RealmData,
)
from dotenv import load_dotenv
from httpx import AsyncClient
import pandas as pd
import asyncio
import duckdb
import os


async def write_item_classes(
    con: duckdb.DuckDBPyConnection,
    bucket: str,
    classes: list[ItemClassData],
    subclasses: list[ItemSubclassData],
):
    classes_path = f"s3://{bucket}/data/static/item_classes.parquet"
    df = pd.DataFrame([c.model_dump() for c in classes])  # noqa: F841 # type: ignore
    con.execute(
        "COPY (SELECT * FROM df ORDER BY id) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
        [classes_path],
    )
    subclasses_path = f"s3://{bucket}/data/static/item_subclasses.parquet"
    df = pd.DataFrame([s.model_dump() for s in subclasses])  # noqa: F841 # type: ignore
    con.execute(
        "COPY (SELECT * FROM df ORDER BY class_id, id) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
        [subclasses_path],
    )


async def write_items(
    con: duckdb.DuckDBPyConnection,
    bucket: str,
    items: list[ItemData],
):
    path = f"s3://{bucket}/data/static/items.parquet"
    df = pd.DataFrame([i.model_dump() for i in items])  # noqa: F841 # type: ignore
    con.execute(
        "COPY (SELECT * FROM df ORDER BY id) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
        [path],
    )


async def write_realms(
    con: duckdb.DuckDBPyConnection, bucket: str, realms: list[RealmData]
):
    path = f"s3://{bucket}/data/static/realms.parquet"
    df = pd.DataFrame([r.model_dump() for r in realms])  # noqa: F841 # type: ignore
    con.execute(
        "COPY (SELECT * FROM df ORDER BY id) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
        [path],
    )


async def main():
    load_dotenv()

    BNET_CLIENT_ID = os.getenv("BNET_CLIENT_ID") or ""
    BNET_CLIENT_SECRET = os.getenv("BNET_CLIENT_SECRET") or ""
    BNET_REGION = os.getenv("BNET_REGION") or ""
    BNET_LOCALE = os.getenv("BNET_LOCALE") or ""

    R2_ID = os.getenv("R2_ACCESS_KEY_ID") or ""
    R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY") or ""
    R2_URL = os.getenv("R2_ENDPOINT_URL") or ""
    R2_BUCKET = os.getenv("R2_BUCKET_NAME") or ""

    client = BlizzardClient(
        BNET_CLIENT_ID, BNET_CLIENT_SECRET, BNET_REGION, BNET_LOCALE
    )

    with duckdb.connect() as con:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"SET s3_access_key_id='{R2_ID}';")
        con.execute(f"SET s3_secret_access_key='{R2_SECRET}';")
        endpoint = R2_URL.replace("https://", "")
        con.execute(f"SET s3_endpoint='{endpoint}';")
        con.execute("SET s3_region='auto';")
        con.execute("SET s3_url_style='path';")

        async with AsyncClient(timeout=60.0) as http_client:
            realms = await client.get_realms(http_client)
            await write_realms(con, R2_BUCKET, realms)
            classes, subclasses = await client.get_item_classes(http_client)
            await write_item_classes(con, R2_BUCKET, classes, subclasses)
            items = await client.get_items(http_client)
            await write_items(con, R2_BUCKET, items)


if __name__ == "__main__":
    asyncio.run(main())
