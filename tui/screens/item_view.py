from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Button
from textual.containers import Horizontal, Vertical, Container
from textual_plotext import PlotextPlot
from datetime import datetime, timedelta
from api.database_manager import DatabaseManager


class ItemViewScreen(Screen):
    CSS_PATH = ["../tcss/item_view_screen.tcss"]

    QUALITY_COLORS = {
        "Poor": "#9d9d9d",
        "Common": "#ffffff",
        "Uncommon": "#1eff00",
        "Rare": "#0070dd",
        "Epic": "#a335ee",
        "Legendary": "#ff8000",
    }

    def __init__(
        self,
        db: DatabaseManager,
        item_id: int,
        realm_id: int,
        commodity: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.db = db
        self.item_id = item_id
        self.realm_id = realm_id
        self.commodity = commodity

        self.item_data = self.db.get_item_data(self.item_id)

    def compose(self) -> ComposeResult:
        item_class = self.db.get_item_class_name(self.item_data.item_class_id)
        item_subclass = self.db.get_item_subclass_name(
            self.item_data.item_class_id, self.item_data.item_subclass_id
        )
        realm_name = self.db.get_realm_by_id(self.realm_id)
        listings = self.db.get_current_listings(
            self.item_id, self.realm_id, commodity=self.commodity
        )
        duration_counts = self.db.get_duration_counts(
            self.item_id, self.realm_id, commodity=self.commodity
        )

        min_price = listings.min_price if listings else 0
        median_price = listings.median_price if listings else 0
        market_value = listings.market_value if listings else 0
        qty_listed = listings.quantity_listed if listings else 0
        auction_count = listings.auction_count if listings else 0
        avg_stack = listings.avg_stack if listings else 0.0

        realm_prices = self.db.get_price_on_each_realm(self.item_id)

        with Container(id="item-view-container"):
            with Horizontal(id="topbar"):
                yield Button("Back", id="back-button")
                yield Label(self.item_data.name, id="item-name")

                quality_label = Label(
                    self.item_data.quality or "Common", id="quality-label"
                )
                quality_label.styles.color = self.QUALITY_COLORS.get(
                    self.item_data.quality or "", "#ffffff"
                )
                yield quality_label

                yield Label(
                    f"{item_class} > {item_subclass}",
                    id="classification",
                )

                yield Label("", classes="spacer")

                yield Label(
                    "Commodity" if self.commodity else realm_name, id="realm-label"
                )

            with Horizontal(id="main-content"):
                with Vertical(id="sidebar"):
                    with Vertical(id="current-listings", classes="sidebar-section"):
                        yield Label("Current Listings", classes="section-header")
                        yield Label(
                            f"min buyout    {self.format_price(min_price)}",
                            classes="stat-row",
                        )
                        yield Label(
                            f"median        {self.format_price(median_price)}",
                            classes="stat-row",
                        )
                        yield Label(
                            f"market value  {self.format_price(market_value)}",
                            classes="stat-row",
                        )

                    with Vertical(id="availability", classes="sidebar-section"):
                        yield Label("Availability", classes="section-header")
                        yield Label(
                            f"qty listed    {qty_listed}",
                            classes="stat-row",
                        )
                        yield Label(
                            f"auctions      {auction_count}",
                            classes="stat-row",
                        )
                        yield Label(
                            f"avg stack     {avg_stack:.1f}",
                            classes="stat-row",
                        )
                        yield Label(
                            f"stackable     {'yes' if self.item_data.stackable else 'no'}",
                            classes="stat-row",
                        )

                    with Vertical(id="duration-split", classes="sidebar-section"):
                        yield Label("Duration Split", classes="section-header")
                        yield Label(
                            f"short         {duration_counts.get('short', 0)}",
                            classes="stat-row",
                        )
                        yield Label(
                            f"medium        {duration_counts.get('medium', 0)}",
                            classes="stat-row",
                        )
                        yield Label(
                            f"long          {duration_counts.get('long', 0)}",
                            classes="stat-row",
                        )
                        yield Label(
                            f"very long     {duration_counts.get('very_long', 0)}",
                            classes="stat-row",
                        )

                    with Vertical(id="comparisons", classes="sidebar-section"):
                        vendor_price = self.item_data.sell_price or 1
                        cost = min_price or 1
                        profit_percent = ((vendor_price - cost) / cost) * 100
                        yield Label(
                            f"vendor price    {self.format_price(self.item_data.sell_price)}",
                            classes="stat-row",
                        )
                        yield Label(
                            f"vendor profit   {profit_percent:.2f}%",
                            classes="stat-row",
                        )
                        yield Label(
                            f"market cap      {self.format_price(int(qty_listed * avg_stack * (median_price or 0)))}",
                            classes="stat-row",
                        )
                        if not self.commodity:
                            yield Label(
                                f"highest realm   {realm_prices[-1][0]}",
                                classes="stat-row",
                            )
                            yield Label(
                                f"lowest realm    {realm_prices[0][0]}",
                                classes="stat-row",
                            )

                with Container(id="charts"):
                    with Vertical():
                        with Horizontal(id="top-charts"):
                            yield PlotextPlot(id="price-history")
                            yield PlotextPlot(id="price-histogram")
                        with Horizontal(id="bottom-charts"):
                            if not self.commodity:
                                yield PlotextPlot(id="cheapest-realms")
                                yield PlotextPlot(id="expensive-realms")
                            else:
                                yield PlotextPlot(id="price-per-day")
                                yield PlotextPlot(id="price-hourly")

    def on_mount(self) -> None:
        realm_prices = self.db.get_price_on_each_realm(self.item_id)

        self.create_price_history_plot()
        self.create_price_histogram()

        if self.commodity:
            self.create_price_by_hour_plot()
            self.create_price_by_dow_plot()
        else:
            max_lines = 25
            self.create_cheapest_realms_plot(realm_prices[:max_lines])
            self.create_expensive_realms_plot(realm_prices[::-1][:max_lines])

    def create_price_history_plot(self) -> None:
        data = self.db.get_price_history(self.item_id, self.realm_id, self.commodity)
        if not data:
            return

        cutoff = datetime.now() - timedelta(weeks=2)
        data = [(datetime.fromisoformat(ts), price) for ts, price in data]
        data = [(ts, price) for ts, price in data if ts >= cutoff]
        if not data:
            return

        time = [ts.strftime("%d/%m/%Y") for ts, _ in data]
        price = [price for _, price in data]

        plt = self.query_one("#price-history", PlotextPlot).plt
        plt.plot(time, price)
        plt.title("Price History")
        max_price = max(price) if price else 0
        upper_limit = max_price * 1.05 if max_price > 0 else 1
        plt.ylim(0, upper_limit)
        plt.yfrequency(5)
        step = upper_limit / 5
        plt.yticks(
            [i * step for i in range(6)],
            [self.format_price_plain(int(i * step)) for i in range(6)],
        )
        plt.canvas_color("none")
        plt.axes_color("none")
        plt.date_form("m/d/Y")

    def create_price_histogram(self) -> None:
        data = self.db.get_price_histogram(self.item_id, self.realm_id, self.commodity)
        if not data:
            return

        buckets = [self.format_price_plain(floor) for floor, _ in data]
        counts = [count for _, count in data]

        plt = self.query_one("#price-histogram", PlotextPlot).plt
        plt.bar(buckets, counts)
        plt.title("Price Distribution")
        plt.canvas_color("none")
        plt.axes_color("none")
        max_count = max(counts) if counts else 1
        plt.ylim(0, max_count * 1.1)

    def create_price_by_hour_plot(self) -> None:
        data = self.db.get_price_by_hour(self.item_id)
        if not data:
            return

        hour_labels = {
            0: "12am",
            1: "1am",
            2: "2am",
            3: "3am",
            4: "4am",
            5: "5am",
            6: "6am",
            7: "7am",
            8: "8am",
            9: "9am",
            10: "10am",
            11: "11am",
            12: "12pm",
            13: "1pm",
            14: "2pm",
            15: "3pm",
            16: "4pm",
            17: "5pm",
            18: "6pm",
            19: "7pm",
            20: "8pm",
            21: "9pm",
            22: "10pm",
            23: "11pm",
        }

        labels = [hour_labels[hour] for hour, _ in data]
        prices = [price for _, price in data]

        plt = self.query_one("#price-hourly", PlotextPlot).plt
        plt.bar(labels, prices, orientation="horizontal")
        plt.title("Min Price by Hour")
        plt.canvas_color("none")
        plt.axes_color("none")
        plt.xlim(0, max(prices) * 1.1)
        step = max(prices) / 5
        plt.xticks(
            [i * step for i in range(6)],
            [self.format_price_plain(int(i * step)) for i in range(6)],
        )

    def create_price_by_dow_plot(self) -> None:
        data = self.db.get_price_by_dow(self.item_id)
        if not data:
            return

        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        labels = [days[dow] for dow, _ in data]
        prices = [price for _, price in data]

        plt = self.query_one("#price-per-day", PlotextPlot).plt
        plt.bar(labels, prices, orientation="horizontal")
        plt.title("Min Price by Day")
        plt.canvas_color("none")
        plt.axes_color("none")
        plt.xlim(0, max(prices) * 1.1)
        step = max(prices) / 5
        plt.xticks(
            [i * step for i in range(6)],
            [self.format_price_plain(int(i * step)) for i in range(6)],
        )

    def create_cheapest_realms_plot(self, data: list[tuple[str, int]]) -> None:
        if not data:
            return
        data = data[::-1]

        realms = [realm for realm, _ in data]
        prices = [price for _, price in data]

        plt = self.query_one("#cheapest-realms", PlotextPlot).plt
        plt.bar(realms, prices, orientation="horizontal", width=0.5)
        plt.title("Cheapest Realms")
        plt.xlim(0, max(prices) * 1.1)
        plt.xticks(
            [i * max(prices) / 5 for i in range(6)],
            [self.format_price_plain(int(i * max(prices) / 5)) for i in range(6)],
        )
        plt.canvas_color("none")
        plt.axes_color("none")

    def create_expensive_realms_plot(self, data: list[tuple[str, int]]) -> None:
        if not data:
            return
        data = data[::-1]

        realms = [realm for realm, _ in data]
        prices = [price for _, price in data]

        plt = self.query_one("#expensive-realms", PlotextPlot).plt
        plt.bar(realms, prices, orientation="horizontal")
        plt.title("Most Expensive Realms")
        plt.xlim(0, max(prices) * 1.1)
        plt.xticks(
            [i * max(prices) / 5 for i in range(6)],
            [self.format_price_plain(int(i * max(prices) / 5)) for i in range(6)],
        )
        plt.canvas_color("none")
        plt.axes_color("none")

    @on(Button.Pressed, "#back-button")
    def close_screen(self) -> None:
        self.app.pop_screen()

    def format_price_plain(self, copper: int | None) -> str:
        if copper is None:
            return "---"
        gold = copper // 10000
        silver = (copper % 10000) // 100
        copper_remaining = copper % 100
        parts = []
        if gold:
            parts.append(f"{gold:,}g")
        if silver and gold < 10:
            parts.append(f"{silver}s")
        if copper_remaining and gold < 10 and silver < 10:
            parts.append(f"{copper_remaining}c")
        if not parts:
            parts.append(f"{copper_remaining}c")
        return " ".join(parts)

    def format_price(self, copper: int | None) -> str:
        if copper is None:
            return "---"
        GOLD = "[#FFD700]"
        SILVER = "[#ADB9E3]"
        COPPER = "[#FF8C58]"
        CLOSE = "[/]"
        gold = copper // 10000
        silver = (copper % 10000) // 100
        copper_remaining = copper % 100
        parts = []
        if gold:
            parts.append(f"{GOLD}{gold:,}g{CLOSE}")
        if silver and gold < 10:
            parts.append(f"{SILVER}{silver}s{CLOSE}")
        if copper_remaining and gold < 10 and silver < 10:
            parts.append(f"{COPPER}{copper_remaining}c{CLOSE}")
        if not parts:
            parts.append(f"{COPPER}{copper_remaining}c{CLOSE}")
        return " ".join(parts)
