from duckdb import DuckDBPyConnection


class DatabaseManager:
    def __init__(self, con: DuckDBPyConnection) -> None:
        self.realms = None
        self.items = None
        self.item_classes = None
        self.item_subclasses = None
        self.con = con

    def get_realms(self) -> list[tuple[int, str]]:
        if self.realms:
            return self.realms
        self.realms = self.con.sql(
            "SELECT id, name FROM realms ORDER BY name;"
        ).fetchall()
        return self.realms
