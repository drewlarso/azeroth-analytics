from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Button


class ItemViewScreen(Screen):
    def __init__(self, item_id: int, **kwargs):
        super().__init__(**kwargs)
        self.item_id = item_id

    def compose(self) -> ComposeResult:
        yield Button("Back", id="back-button")
        yield Label("hello")

    @on(Button.Pressed, "#back-button")
    def close_screen(self) -> None:
        self.app.pop_screen()
