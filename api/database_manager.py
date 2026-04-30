from duckdb import DuckDBPyConnection
from bnet.models import ItemData


class DatabaseManager:
    def __init__(self, con: DuckDBPyConnection) -> None:
        self.realms = None
        self.items = None
        self.item_classes = None
        self.item_subclasses = {}
        self.con = con

    def get_realms(self) -> dict[str, int]:
        if self.realms:
            return self.realms

        realm_list = self.con.sql(
            "SELECT name, id FROM realms ORDER BY name"
        ).fetchall()
        self.realms = {name: id for name, id in realm_list}

        return self.realms

    def get_item_classes(self) -> dict[str, int]:
        if self.item_classes:
            return self.item_classes

        item_classes_list = self.con.sql(
            "SELECT name, id FROM classes ORDER BY name"
        ).fetchall()
        self.item_classes = {name: id for name, id in item_classes_list}

        return self.item_classes

    def get_item_subclasses(self, class_id: int) -> dict[str, int]:
        if class_id in self.item_subclasses:
            return self.item_subclasses[class_id]

        item_subclasses_list = self.con.sql(
            "SELECT name, id FROM subclasses WHERE class_id = ? ORDER BY name",
            params=[class_id],
        ).fetchall()
        self.item_subclasses[class_id] = {name: id for name, id in item_subclasses_list}

        return self.item_subclasses[class_id]

    def search_items(
        self,
        search_term: str = "",
        item_class: int | None = None,
        item_subclass: int | None = None,
        realm_id: int | None = None,
    ) -> list[ItemData]:
        query = """
            SELECT DISTINCT i.*
            FROM items i
            WHERE 1=1
        """
        params: list[int | str] = []

        if search_term:
            query += " AND i.name ILIKE ?"
            params.append(f"%{search_term}%")

        if item_class:
            query += " AND i.item_class_id = ?"
            params.append(item_class)

        if item_subclass:
            query += " AND i.item_subclass_id = ?"
            params.append(item_subclass)

        if realm_id is None:
            query += """
                AND i.id IN (
                    SELECT item_id FROM auction_items
                    UNION
                    SELECT item_id FROM commodity_items
                )
            """
        else:
            query += """
                AND i.id IN (
                    SELECT item_id FROM commodity_items
                    UNION
                    SELECT item_id FROM auction_items WHERE realm_id = ?
                )
            """
            params.append(realm_id)

        query += " LIMIT 100;"

        items = self.con.execute(query, params).df().to_dict("records")
        return [ItemData(**item) for item in items]  # type: ignore
