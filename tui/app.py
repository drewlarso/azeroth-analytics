from textual.app import App
from api.database_manager import DatabaseManager
from .screens.search import SearchScreen
from .screens.item_view import ItemViewScreen
import duckdb


class AnalyticsApp(App):
    TITLE = "Azeroth Analytics"
    BINDINGS = [("escape", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.con = duckdb.connect("azeroth.db")
        self.database = DatabaseManager(self.con)

    def on_mount(self) -> None:
        self.theme = "tokyo-night"
        search_screen = SearchScreen(db=self.database)
        self.push_screen(search_screen)
        self.push_screen(ItemViewScreen(db=self.database, item_id=83088, realm_id=60))
