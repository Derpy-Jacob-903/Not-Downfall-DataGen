from dataclasses import dataclass
from typing import Callable
import plotly.graph_objects as go

from data import prep_cards
from .cards import fig_cards, fig_cards_sp, fig_cards_mp, fig_cards_sp_vs_mp
from .character import fig_ascension, fig_daily, fig_survival
from .relics import fig_relics


@dataclass
class TabDefinition:
    id: str
    label: str
    builder: Callable[[], go.Figure]


def get_tabs() -> list[TabDefinition]:
    """Fetch shared dependencies once and construct all registered dashboard tabs."""
    try:
        cards_df = prep_cards()
    except Exception as e:
        print(f"card_stats fetch failed, all card tabs skipped: {e}")
        cards_df = None

    tabs = []

    if cards_df is not None:
        tabs.extend([
            TabDefinition("cards", "Card explorer", lambda: fig_cards(cards_df)),
            TabDefinition("cards_sp", "Cards - singleplayer", lambda: fig_cards_sp(cards_df)),
            TabDefinition("cards_mp", "Cards - multiplayer", lambda: fig_cards_mp(cards_df)),
            TabDefinition("cards_gap", "Cards - SP vs MP", lambda: fig_cards_sp_vs_mp(cards_df)),
        ])

    tabs.extend([
        TabDefinition("ascension", "Winrate x ascension", fig_ascension),
        TabDefinition("daily", "Winrate x day", fig_daily),
        TabDefinition("survival", "Floor survival", fig_survival),
        TabDefinition("relics", "Relic winrate", fig_relics),
    ])

    return tabs