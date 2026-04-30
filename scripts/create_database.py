import duckdb
import os

if __name__ == "__main__":
    file_path = "azeroth.db"

    if os.path.exists(file_path):
        os.remove(file_path)

    con = duckdb.connect(file_path)

    con.execute(
        "CREATE VIEW auctions AS SELECT * FROM read_parquet('data/auctions/**/*.parquet')"
    )
    con.execute(
        "CREATE VIEW commodities AS SELECT * FROM read_parquet('data/commodities/**/*.parquet')"
    )
    con.execute(
        "CREATE VIEW all_items AS SELECT * FROM read_parquet('data/static/items.parquet')"
    )
    con.execute(
        "CREATE TABLE auction_items AS SELECT DISTINCT realm AS realm_id, item_id FROM auctions"
    )
    con.execute(
        "CREATE TABLE commodity_items AS SELECT DISTINCT item_id FROM commodities"
    )
    con.execute(
        "CREATE VIEW classes AS SELECT * FROM read_parquet('data/static/item_classes.parquet')"
    )
    con.execute(
        "CREATE VIEW subclasses AS SELECT * FROM read_parquet('data/static/item_subclasses.parquet')"
    )
    con.execute(
        "CREATE VIEW realms AS SELECT * FROM read_parquet('data/static/realms.parquet')"
    )

    con.execute("""
        CREATE TABLE items AS 
        SELECT * FROM all_items
        WHERE id IN (
            SELECT item_id FROM auction_items
            UNION
            SELECT item_id FROM commodity_items
        )
    """)
    con.execute(
        "CREATE INDEX auction_items_realm_item_idx ON auction_items(realm_id, item_id)"
    )
    con.execute("CREATE INDEX commodity_items_item_idx ON commodity_items(item_id)")
    con.execute("CREATE INDEX items_id_idx ON items(id)")

    con.close()
