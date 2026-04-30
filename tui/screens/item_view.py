from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Button
from textual.containers import Grid


class ItemViewScreen(Screen):
    CSS_PATH = ["../tcss/item_view_screen.tcss"]

    def __init__(self, item_id: int, realm_id: int, commodity: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.item_id = item_id
        self.realm_id = realm_id
        self.commodity = commodity

    def compose(self) -> ComposeResult:
        with Grid(id="item-view-container"):
            yield Button("Back", id="back-button")
            yield Label(str(self.item_id))
            yield Label(str(self.realm_id))
            yield Label("Commodity" if self.commodity else "Auction")

    @on(Button.Pressed, "#back-button")
    def close_screen(self) -> None:
        self.app.pop_screen()
