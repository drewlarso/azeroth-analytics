from textual.app import App, ComposeResult
from textual.widgets import Label


class AnalyticsApp(App):
    CSS = """
    Label {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        self.theme = "catppuccin-mocha"

        yield Label("Hello Azeroth!")
