from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Button
from textual.containers import Horizontal, Vertical, Container
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

        min_price = listings.min_price if listings else None
        median_price = listings.median_price if listings else None
        market_value = listings.market_value if listings else None
        qty_listed = listings.quantity_listed if listings else 0
        auction_count = listings.auction_count if listings else 0
        avg_stack = listings.avg_stack if listings else 0.0

        with Container(id="item-view-container"):
            with Horizontal():
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

                yield Label("Vendor Price: 25g", id="vendor-price")
                yield Label(realm_name, id="realm-label")

            with Vertical(id="basic-stats"):
                with Vertical(id="current-listings", classes="sidebar-section"):
                    yield Label("Current Listings", classes="section-header")
                    yield Label(
                        f"min buyout    {self.format_price(min_price)}",
                        classes="stat-row",
                        id="stat-min-price",
                    )
                    yield Label(
                        f"median        {self.format_price(median_price)}",
                        classes="stat-row",
                        id="stat-median-price",
                    )
                    yield Label(
                        f"market value  {self.format_price(market_value)}",
                        classes="stat-row",
                        id="stat-market-value",
                    )

            with Vertical(id="availability", classes="sidebar-section"):
                yield Label("Availability", classes="section-header")
                yield Label(
                    f"qty listed    {qty_listed}",
                    classes="stat-row",
                    id="stat-qty",
                )
                yield Label(
                    f"auctions      {auction_count}",
                    classes="stat-row",
                    id="stat-auctions",
                )
                yield Label(
                    f"avg stack     {avg_stack:.1f}",
                    classes="stat-row",
                    id="stat-avg-stack",
                )
                yield Label(
                    f"stackable     {'yes' if self.item_data.stackable else 'no'}",
                    classes="stat-row",
                    id="stat-stackable",
                )

            with Vertical(id="duration-split", classes="sidebar-section"):
                yield Label("Duration Split", classes="section-header")
                yield Label(
                    f"short         {duration_counts.get('short', 0)}",
                    classes="stat-row",
                    id="stat-dur-short",
                )
                yield Label(
                    f"medium        {duration_counts.get('medium', 0)}",
                    classes="stat-row",
                    id="stat-dur-medium",
                )
                yield Label(
                    f"long          {duration_counts.get('long', 0)}",
                    classes="stat-row",
                    id="stat-dur-long",
                )
                yield Label(
                    f"very long     {duration_counts.get('very_long', 0)}",
                    classes="stat-row",
                    id="stat-dur-very-long",
                )

    @on(Button.Pressed, "#back-button")
    def close_screen(self) -> None:
        self.app.pop_screen()

    def format_price(self, copper: int | None) -> str:
        if copper is None:
            return "---"

        gold = copper // 10000
        silver = (copper % 10000) // 100
        copper_remaining = copper % 100

        parts = []
        if gold:
            parts.append(f"{gold}g")
        if silver:
            parts.append(f"{silver}s")
        if copper_remaining or not parts:
            parts.append(f"{copper_remaining}c")
        return " ".join(parts)
