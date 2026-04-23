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
        "CREATE VIEW items AS SELECT * FROM read_parquet('data/static/items.parquet')"
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

    con.close()
