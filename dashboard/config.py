import os
import colorsys

KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
SUPABASE_URL = "https://wxememsxgrgrfvntulgr.supabase.co"

# Palette configuration
S, V = 0.65, 0.80
ORDER = [
    "HERMIT-HERMIT", "GUARDIAN-GUARDIAN", "AUTOMATON-AUTOMATON", "SLIMEBOSS-SLIME_BOSS",
    "SNECKO-SNECKO", "AWAKENED-AWAKENED", "CHAMP-CHAMP", "HEXAGHOST-HEXAGHOST"
]
CHAR_ORDER = [c.split("-")[0] for c in ORDER]

COLORS = {}
for i, name in enumerate(CHAR_ORDER):
    rr, gg, bb = colorsys.hsv_to_rgb(i / len(CHAR_ORDER), S, V)
    COLORS[name] = f"#{int(rr * 255):02X}{int(gg * 255):02X}{int(bb * 255):02X}"
COLORS["COLORLESS"] = "#999999"


def char_of(entity_name: str) -> str:
    """Extract character prefix or fall back to COLORLESS."""
    prefix = str(entity_name).split("-", 1)[0]
    return prefix if prefix in set(CHAR_ORDER) else "COLORLESS"