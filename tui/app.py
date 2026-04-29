from textual.app import App, ComposeResult
from textual.widgets import Header
from api.database_manager import DatabaseManager
import duckdb


class AnalyticsApp(App):
    TITLE = "Azeroth Analytics"

    def __init__(self):
        super().__init__()
        self.con = duckdb.connect("azeroth.db")
        self.database = DatabaseManager(self.con)

    def compose(self) -> ComposeResult:
        self.theme = "rose-pine"

        yield Header()

    async def on_unmount(self) -> None:
        self.con.close()
