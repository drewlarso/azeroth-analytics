from bnet.client import BlizzardClient, AuctionData, RealmData
from datetime import datetime, timezone
from dotenv import load_dotenv
from httpx import AsyncClient
import pandas as pd
import asyncio
import duckdb
import os


async def write_commodities(
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


async def write_auctions(
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


async def process_realm_auctions(
    bnet_client: BlizzardClient,
    http_client: AsyncClient,
    con: duckdb.DuckDBPyConnection,
    bucket: str,
    realm: RealmData,
    region: str,
    timestamp: datetime,
    touched_ids: set[int],
):
    if realm.id in touched_ids:
        return
    touched_ids.add(realm.id)

    try:
        auctions = await bnet_client.get_auctions(http_client, realm.id)
        await write_auctions(con, bucket, auctions, realm.id, region, timestamp)
        print(f"Saved data for {realm.name} (id={realm.id}) - {len(auctions)} items")
    except Exception as e:
        print(f"Failed to process realm {realm.id}: {e}")


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
    timestamp = datetime.now(timezone.utc)

    with duckdb.connect() as con:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"SET s3_access_key_id='{R2_ID}';")
        con.execute(f"SET s3_secret_access_key='{R2_SECRET}';")
        endpoint = R2_URL.replace("https://", "")
        con.execute(f"SET s3_endpoint='{endpoint}';")
        con.execute("SET s3_region='auto';")
        con.execute("SET s3_url_style='path';")

        async with AsyncClient(timeout=60.0) as http_client:
            print("Fetching commodities...")
            commodities = await client.get_commodities(http_client)
            await write_commodities(con, R2_BUCKET, commodities, BNET_REGION, timestamp)
            print(f"Saved commodities ({len(commodities)} items)")

            realms = await client.get_realms(http_client)
            touched_realm_ids = set()

            tasks = [
                process_realm_auctions(
                    client,
                    http_client,
                    con,
                    R2_BUCKET,
                    realm,
                    BNET_REGION,
                    timestamp,
                    touched_realm_ids,
                )
                for realm in realms
            ]

            await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
