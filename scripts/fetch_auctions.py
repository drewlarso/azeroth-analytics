from api.client import BlizzardClient, AuctionData
from datetime import datetime, timezone
from dotenv import load_dotenv
import pandas as pd
import duckdb
import os


def write_commodities(
    con: duckdb.DuckDBPyConnection,
    bucket: str,
    auctions: list[AuctionData],
    region: str,
    timestamp: datetime,
):
    path = (
        f"s3://{bucket}/data/commodities/region={region}"
        f"/year={timestamp.year}/month={timestamp.month:02d}"
        f"/day={timestamp.day:02d}/hour={timestamp.hour:02d}/data.parquet"
    )
    df = pd.DataFrame([a.model_dump() for a in auctions])  # noqa: F841 # type: ignore
    con.execute(
        "COPY (SELECT * FROM df ORDER BY item_id) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
        [path],
    )


def write_auctions(
    con: duckdb.DuckDBPyConnection,
    bucket: str,
    auctions: list[AuctionData],
    realm_id: int,
    region: str,
    timestamp: datetime,
):
    path = (
        f"s3://{bucket}/data/auctions/region={region}/realm={realm_id}"
        f"/year={timestamp.year}/month={timestamp.month:02d}"
        f"/day={timestamp.day:02d}/hour={timestamp.hour:02d}/data.parquet"
    )
    df = pd.DataFrame([a.model_dump() for a in auctions])  # noqa: F841 # type: ignore
    con.execute(
        "COPY (SELECT * FROM df ORDER BY item_id) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
        [path],
    )


if __name__ == "__main__":
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
    timestamp = datetime.now(timezone.utc)

    with duckdb.connect() as con:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"SET s3_access_key_id='{R2_ID}';")
        con.execute(f"SET s3_secret_access_key='{R2_SECRET}';")

        endpoint = R2_URL.replace("https://", "")
        con.execute(f"SET s3_endpoint='{endpoint}';")
        con.execute("SET s3_region='auto';")
        con.execute("SET s3_url_style='path';")

        commodities = client.get_commodities()
        write_commodities(con, R2_BUCKET, commodities, BNET_REGION, timestamp)

        realms = client.get_realms()
        touched_realm_ids = set[int]()

        for realm in realms:
            if realm.id in touched_realm_ids:
                continue
            auctions = client.get_auctions(realm.id)
            touched_realm_ids.add(realm.id)
            write_auctions(con, R2_BUCKET, auctions, realm.id, BNET_REGION, timestamp)
            print(f"saved data for {realm.name} (id={realm.id})")
