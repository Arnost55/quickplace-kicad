"""QuickPlace PCB footprint placement plugin."""

try:
    import pcbnew
except ImportError:
    pcbnew = None

if pcbnew is not None and pcbnew.GetBoard() is not None:
    from .plugin import QuickPlacePlugin
    QuickPlacePlugin().register()
