from pathlib import Path
import os

import duckdb
from dotenv import load_dotenv


DB_PATH = Path("data/analytics.duckdb")


def configure_r2(con: duckdb.DuckDBPyConnection) -> str:
    r2_id = os.getenv("R2_ACCESS_KEY_ID") or ""
    r2_secret = os.getenv("R2_SECRET_ACCESS_KEY") or ""
    r2_url = os.getenv("R2_ENDPOINT_URL") or ""
    r2_bucket = os.getenv("R2_BUCKET_NAME") or ""

    if not all([r2_id, r2_secret, r2_url, r2_bucket]):
        raise ValueError("Missing one or more required R2 environment variables.")

    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_access_key_id='{r2_id}';")
    con.execute(f"SET s3_secret_access_key='{r2_secret}';")
    con.execute(f"SET s3_endpoint='{r2_url.removeprefix('https://')}';")
    con.execute("SET s3_region='auto';")
    con.execute("SET s3_url_style='path';")

    return r2_bucket


def create_views(con: duckdb.DuckDBPyConnection, bucket: str) -> None:
    auctions_path = f"s3://{bucket}/data/auctions/**/*.parquet"
    commodities_path = f"s3://{bucket}/data/commodities/**/*.parquet"
    auctions_sql_path = auctions_path.replace("'", "''")
    commodities_sql_path = commodities_path.replace("'", "''")

    con.execute(
        f"""
        CREATE OR REPLACE VIEW auctions AS
        SELECT *
        FROM read_parquet('{auctions_sql_path}', hive_partitioning = true)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW commodities AS
        SELECT *
        FROM read_parquet('{commodities_sql_path}', hive_partitioning = true)
        """
    )


def main() -> None:
    load_dotenv()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(DB_PATH)) as con:
        bucket = configure_r2(con)
        create_views(con, bucket)

    print(f"Created {DB_PATH} with views: auctions, commodities")


if __name__ == "__main__":
    main()
