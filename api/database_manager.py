from duckdb import DuckDBPyConnection
from bnet.models import ItemData, ListingStats


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

    def get_item_class_name(self, class_id: int) -> str:
        name = self.con.sql(
            "SELECT name FROM classes WHERE id = ?",
            params=[class_id],
        ).fetchall()[0][0]

        return name or ""

    def get_item_subclass_name(self, class_id: int, subclass_id: int) -> str:
        name = self.con.sql(
            "SELECT name FROM subclasses WHERE id = ? and class_id = ?",
            params=[subclass_id, class_id],
        ).fetchall()[0][0]

        return name or ""

    def get_realm_by_id(self, realm_id: int) -> str:
        name = self.con.sql(
            "SELECT name FROM realms WHERE id = ?",
            params=[realm_id],
        ).fetchall()[0][0]

        return name or ""

    def get_item_data(self, item_id) -> ItemData:
        items = (
            self.con.sql("SELECT * FROM items WHERE id = ?", params=[item_id])
            .df()
            .to_dict("records")
        )

        item = items[0]
        return ItemData(**{str(k): v for k, v in item.items()})

    def get_current_listings(
        self, item_id: int, realm_id: int, commodity: bool = False
    ) -> ListingStats | None:
        if commodity:
            row = self.con.execute(
                """
                SELECT
                    MIN(unit_price) AS min_price,
                    MEDIAN(unit_price) AS median_price,
                    PERCENTILE_CONT(0.15) WITHIN GROUP (ORDER BY unit_price) AS market_value,
                    SUM(quantity) AS quantity_listed,
                    COUNT(DISTINCT auction_id) AS auction_count,
                    AVG(quantity) AS average_stack
                FROM recent_commodities
                WHERE item_id = ?
                """,
                [item_id],
            ).fetchone()
        else:
            row = self.con.execute(
                """
                SELECT
                    MIN(unit_price) AS min_price,
                    MEDIAN(unit_price) AS median_price,
                    PERCENTILE_CONT(0.15) WITHIN GROUP (ORDER BY unit_price) AS market_value,
                    SUM(quantity) AS quantity_listed,
                    COUNT(auction_id) AS auction_count,
                    AVG(quantity) AS average_stack
                FROM recent_auctions
                WHERE item_id = ?
                    AND realm = ?
                GROUP BY auction_id
                """,
                [item_id, realm_id],
            ).fetchone()

        if row is None or row[0] is None:
            return None

        return ListingStats(
            min_price=int(row[0]),
            median_price=int(row[1]),
            market_value=int(row[2]),
            quantity_listed=int(row[3]),
            auction_count=int(row[4]),
            avg_stack=float(row[5]),
        )

    def get_duration_counts(
        self, item_id: int, realm_id: int, commodity: bool = False
    ) -> dict[str, int]:
        if commodity:
            rows = self.con.execute(
                """
                SELECT duration, COUNT(*) AS count
                FROM recent_commodities
                WHERE item_id = ?
                GROUP BY duration
                """,
                [item_id],
            ).fetchall()
        else:
            rows = self.con.execute(
                """
                SELECT duration, COUNT(*) AS count
                FROM recent_auctions
                WHERE item_id = ?
                AND realm = ?
                GROUP BY duration
                """,
                [item_id, realm_id],
            ).fetchall()

        return {duration.lower(): count for duration, count in rows}

    def get_price_history(
        self, item_id: int, realm_id: int, commodity: bool = False
    ) -> list[tuple[str, int]]:
        if commodity:
            rows = self.con.execute(
                """
                SELECT
                    TIME_BUCKET(
                        INTERVAL '24 hours',
                        MAKE_TIMESTAMP(year::INT, month::INT, day::INT, hour::INT, 0, 0)
                    ) AS ts,
                    MIN(unit_price)
                FROM commodities
                WHERE item_id = ?
                GROUP BY ts
                ORDER BY ts
                """,
                [item_id],
            )
        else:
            rows = self.con.execute(
                f"""
                SELECT
                    TIME_BUCKET(
                        INTERVAL '24 hours',
                        MAKE_TIMESTAMP(year::INT, month::INT, day::INT, hour::INT, 0, 0)
                    ) AS ts,
                    MIN(unit_price)
                FROM read_parquet('data/auctions/region=us/realm={realm_id}/**/*.parquet')
                WHERE item_id = ?
                GROUP BY ts
                ORDER BY ts
                """,
                [item_id],
            )

        return [(str(timestamp), price) for timestamp, price in rows.fetchall()]

    def get_price_by_hour(self, item_id: int) -> list[tuple[int, float]]:
        rows = self.con.execute(
            """
            SELECT hour::INT AS hour, MIN(unit_price) AS min_price
            FROM commodities
            WHERE item_id = ?
            GROUP BY hour
            ORDER BY hour
            """,
            [item_id],
        ).fetchall()
        return [(int(row[0]), float(row[1])) for row in rows]

    def get_price_by_dow(self, item_id: int) -> list[tuple[int, float]]:
        rows = self.con.execute(
            """
            SELECT
                DAYOFWEEK(MAKE_TIMESTAMP(year::INT, month::INT, day::INT, hour::INT, 0, 0)) AS dow,
                MIN(unit_price) AS min_price
            FROM commodities
            WHERE item_id = ?
            GROUP BY dow
            ORDER BY dow
            """,
            [item_id],
        ).fetchall()
        return [(int(row[0]), float(row[1])) for row in rows]

    def get_price_histogram(
        self, item_id: int, realm_id: int, commodity: bool = False
    ) -> list:
        if commodity:
            row = self.con.execute(
                """
                SELECT histogram(unit_price)
                FROM (
                    SELECT unit_price
                    FROM recent_commodities
                    WHERE item_id = ?
                    GROUP BY auction_id, unit_price
                )
                """,
                [item_id],
            ).fetchone()
        else:
            row = self.con.execute(
                """
                SELECT histogram(unit_price)
                FROM (
                    SELECT unit_price
                    FROM recent_auctions
                    WHERE item_id = ?
                        AND realm = ?
                    GROUP BY auction_id, unit_price
                )
                """,
                [item_id, realm_id],
            ).fetchone()

        if row is None or row[0] is None:
            return []

        hist = row[0]
        return sorted(hist.items())

    def get_price_on_each_realm(self, item_id: int) -> list[tuple[str, int]]:
        rows = self.con.execute(
            """
            SELECT DISTINCT realms.name, MIN(unit_price) as price
            FROM recent_auctions
            JOIN realms
                ON realms.id = recent_auctions.realm
            WHERE item_id = ?
            GROUP BY realms.name
            ORDER BY price, realms.name
            """,
            [item_id],
        )

        return [(realm, price) for realm, price in rows.fetchall()]

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

        query += " ORDER BY i.name LIMIT 100;"

        items = self.con.execute(query, params).df().to_dict("records")
        return [ItemData(**item) for item in items]  # type: ignore
