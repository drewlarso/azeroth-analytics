from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Select, Input, Collapsible, Button
from textual.containers import Horizontal, Vertical, VerticalScroll
from api.database_manager import DatabaseManager
import duckdb


class AnalyticsApp(App):
    TITLE = "Azeroth Analytics"

    CSS_PATH = ["tcss/navbar.tcss", "tcss/sidebar.tcss", "tcss/search_results.tcss"]

    def __init__(self):
        super().__init__()
        self.con = duckdb.connect("azeroth.db")
        self.database = DatabaseManager(self.con)
        self.selected_realm = 0
        self.search_query = "panther"
        self.selected_class = -1
        self.selected_subclass = -1
        self.search_results = []

    def compose(self) -> ComposeResult:
        self.theme = "tokyo-night"

        realms = self.database.get_realms()
        self.selected_realm = realms["Stormrage"]

        with Vertical():
            # Navbar with realm select and item search
            with Horizontal(id="navbar"):
                yield Select(
                    ((name, id) for name, id in realms.items()),
                    id="realm-selector",
                    value=self.selected_realm,
                )
                yield Input(self.search_query, id="item-search")

            with Horizontal():
                # Sidebar With Classes/Subclasses
                with VerticalScroll(id="sidebar"):
                    for c_name, c_id in self.database.get_item_classes().items():
                        with Collapsible(title=c_name):
                            for s_name, s_id in self.database.get_item_subclasses(
                                c_id
                            ).items():
                                yield Button(
                                    s_name,
                                    name=f"{c_id}-{s_id}",
                                    classes="subclass-button",
                                )

                # Search Results
                with VerticalScroll(id="search-results"):
                    pass

    @on(Button.Pressed, ".subclass-button")
    def subclass_button_pressed(self, event: Button.Pressed) -> None:
        if not event.button.name:
            return

        self.search_query = ""
        self.query_one("#item-search", Input).value = self.search_query

        class_id, subclass_id = map(int, event.button.name.split("-"))

        self.selected_class = -1 if class_id == self.selected_class else class_id
        self.selected_subclass = (
            -1 if subclass_id == self.selected_subclass else subclass_id
        )

        self.search_items()

    @on(Select.Changed, "#realm-selector")
    def realm_selected(self, event: Select.Changed) -> None:
        self.selected_realm = event.value

    @on(Input.Changed, "#item-search")
    def searchbar_updated(self, event: Input.Changed) -> None:
        self.search_query = event.value
        self.search_items()

    def search_items(self) -> None:
        if not self.is_mounted:
            return

        self.search_results = self.database.search_items(
            self.search_query or "",
            self.selected_class if self.selected_class >= 0 else None,
            self.selected_subclass if self.selected_subclass >= 0 else None,
        )

        results = self.query_one("#search-results", VerticalScroll)

        results.remove_children()
        for result in self.search_results:
            results.mount(
                Button(result.name, name=str(result.id), classes="result-button")
            )

    async def on_unmount(self) -> None:
        self.con.close()
