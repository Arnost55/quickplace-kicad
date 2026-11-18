"""QuickPlace PCB footprint placement plugin."""

try:
    import pcbnew
except ImportError:
    pass
else:
    if pcbnew.GetBoard() is not None:
        from .plugin import QuickPlacePlugin
        QuickPlacePlugin().register()
