from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Grid, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Input, Select, Collapsible, Button
from api.database_manager import DatabaseManager
from bnet.models import ItemData
from .item_view import ItemViewScreen


class SearchScreen(Screen):
    realm = reactive(-1, init=False)
    search_term = reactive("panther", init=False)
    search_class = reactive(-1, init=False)
    search_subclass = reactive(-1, init=False)
    search_results: reactive[list[ItemData]] = reactive([], init=False)
    selected_item = reactive(-1, init=False)

    CSS_PATH = ["../tcss/search_screen.tcss"]

    def __init__(self, db: DatabaseManager, **kwargs):
        super().__init__(**kwargs)
        self.db = db

    def compose(self) -> ComposeResult:
        realms = self.db.get_realms()
        item_classes = self.db.get_item_classes().items()

        default_realm = "Stormrage"
        self.realm = realms[default_realm]

        with Grid(id="search-screen-container"):
            # Top Bar
            yield Select(
                ((name, name) for name in realms),
                id="realm-selector",
                value=default_realm,
            )
            yield Input(value=self.search_term, id="search-input")

            # Side Bar
            with VerticalScroll(id="sidebar"):
                for item_class, class_id in item_classes:
                    item_subclasses = self.db.get_item_subclasses(class_id).items()
                    with Collapsible(
                        title=item_class, name=str(class_id), classes="class-dropdown"
                    ):
                        for subclass, subclass_id in item_subclasses:
                            yield Button(
                                subclass,
                                name=f"{class_id}-{subclass_id}",
                                classes="subclass-button",
                                flat=True,
                            )

            # Search Results
            with VerticalScroll(id="results"):
                pass

    def watch_selected_item(self, id: int) -> None:
        if id >= 0:
            self.app.push_screen(ItemViewScreen(item_id=id))

    def update_search_results(self):
        self.search_results = self.db.search_items(
            self.search_term,
            self.search_class if self.search_class >= 0 else None,
            self.search_subclass if self.search_subclass >= 0 else None,
        )

        results = self.query_one("#results", VerticalScroll)
        results.remove_children()

        for result in self.search_results:
            results.mount(
                Button(result.name, name=str(result.id), classes="result-item")
            )

        results.scroll_to(y=0, animate=False)

    @on(Select.Changed, "#realm-selector")
    def change_realm(self, event: Select.Changed) -> None:
        if event.value is Select.BLANK:
            return
        realms = self.db.get_realms()
        self.realm = realms[str(event.value)]

    @on(Input.Changed, "#search-input")
    def update_search(self, event: Input.Changed) -> None:
        self.search_term = event.value
        self.update_search_results()

    @on(Collapsible.Expanded, ".class-dropdown")
    def select_class(self, event: Collapsible.Expanded) -> None:
        if not event.collapsible.name:
            return
        self.search_class = int(event.collapsible.name)

        self.search_term = ""
        self.update_search_results()

    @on(Collapsible.Collapsed, ".class-dropdown")
    def clear_search_params(self, event: Collapsible.Collapsed) -> None:
        self.search_class = -1
        self.search_subclass = -1

        self.search_term = ""
        self.update_search_results()

    @on(Button.Pressed, ".subclass-button")
    def select_subclass(self, event: Button.Pressed) -> None:
        if not event.button.name:
            return

        class_id, subclass_id = event.button.name.split("-")
        if subclass_id == self.search_subclass:
            self.search_class = -1
            self.search_subclass = -1
        else:
            self.search_class = int(class_id)
            self.search_subclass = int(subclass_id)

        self.search_term = ""
        self.update_search_results()

    @on(Button.Pressed, ".result-item")
    def select_item(self, event: Button.Pressed) -> None:
        self.selected_item = int(event.button.name or "-1")
