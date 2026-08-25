import os
import colorsys

KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
SUPABASE_URL = "https://poefclgeeqhmtpdcrcev.supabase.co"

# Palette configuration
S, V = 0.65, 0.80
ORDER = [
    #"BLDSURV-BLD_SURV", 
    #"DRUIDSURV-DRUID_SURV", "DRUIDSURV-WIZARD_SURV"
    "JESTER-JESTER",
    "MOONSCREEDPORT-ARCRANE", "MOONSCREEDPORT-AYTEK", "MOONSCREEDPORT-ECHO", "MOONSCREEDPORT-POLARIX",
    "THERAILGUN2-THE_RAILGUN2", 
]
CHAR_ORDER = [c.split("-")[0] for c in ORDER]

COLORS = {}
for i, name in enumerate(CHAR_ORDER):
    rr, gg, bb = colorsys.hsv_to_rgb(i / len(CHAR_ORDER), S, V)
    COLORS[name] = f"#{int(rr * 255):02X}{int(gg * 255):02X}{int(bb * 255):02X}"
COLORS["COLORLESS"] = "#999999"
COLORS["BLDSURV-BLD_SURV"] = "#56a786"
COLORS["DRUIDSURV-DRUID_SURV"] = "#974d2c"
COLORS["DRUIDSURV-WIZARD_SURV"] = "#C45B6F"
COLORS["JESTER-JESTER"] = "#ff00ae"
COLORS["THERAILGUN2-THE_RAILGUN2"] = "#33FFAD"
COLORS["MOONSCREEDPORT-ARCRANE"] = "#bbdb44"
COLORS["MOONSCREEDPORT-AYTEK"] = "#f65d34"
COLORS["MOONSCREEDPORT-ECHO"] = "#3dd9ca"
COLORS["MOONSCREEDPORT-POLARIX"] = "#D780FF"


def char_of(entity_name: str) -> str:
    """Extract character prefix or fall back to COLORLESS."""
    prefix = str(entity_name).split("-", 1)[0]
    return prefix if prefix in set(CHAR_ORDER) else "COLORLESS"
