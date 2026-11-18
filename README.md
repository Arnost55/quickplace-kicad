# QuickPlace for KiCad 10

QuickPlace is an offline PCB Editor Action Plugin for conservative, connectivity-aware footprint placement. It does **not** route traces, modify a schematic or netlist, or perform electrical design-rule checking. The current implementation uses Python's standard library and the `pcbnew`/`wx` modules bundled with KiCad 10.

## Install on Windows 11

1. Install KiCad **10 stable**. Tested against KiCad **10.0.6**; other minor versions should be tested before production use.
### Install directly from the repository (KiCad Plugin and Content Manager)

1. Download the `quickplace-pcm.zip` asset from the [GitHub Releases page](https://github.com/Arnost55/quickplace-kicad/releases). If there is no release yet, download `dist/quickplace-pcm.zip` from the repository's Code page (open `dist/` and choose the file's **Download raw file** action).
2. In KiCad, open **Plugin and Content Manager** from the **Tools** menu and choose **Install from File…**.
3. Select `quickplace-pcm.zip`, confirm installation, then restart PCB Editor if requested.

This is a proper PCM archive with the required root `metadata.json` and `plugins/` layout. The GitHub repository itself is not a PCM index, so it will not appear automatically in the PCM browser. The archive can be installed directly using **Install from File…**; discoverability in the browser requires a repository index (or acceptance into KiCad's official addon index).

### Manual Action Plugin installation

1. Install KiCad **10 stable**. Tested against KiCad **10.0.6**; other minor versions should be tested before production use.
2. Download and extract `dist/quickplace-kicad10.zip`. Copy the enclosed `quickplace` folder (not its individual files) into `%USERPROFILE%\\Documents\\KiCad\\10.0\\scripting\\plugins`. The actual Documents folder may be redirected: use the plugin folder button in **PCB Editor → Preferences → PCB Editor → Plugins** if unsure.
3. Alternatively run `powershell -ExecutionPolicy Bypass -File .\\install.ps1` from this repository, optionally passing `-PluginDirectory 'your\\plugins\\path'`. The installer refuses to overwrite an existing installation.
4. Open a board, then choose **Refresh Plugins** from the plugin menu (the menu may be labeled **Tools → Plugins** in your build; the KiCad 10 manual calls the Action Plugin submenu **Tools → External Plugins**). QuickPlace should appear as **QuickPlace Now** after the refresh; restart PCB Editor if it does not. The screenshot's **fast route autorouter** is a separate plugin: QuickPlace places footprints and does not autoroute tracks. If QuickPlace is missing, open **Preferences → PCB Editor → Action Plugins → Open Plugin Directory** and ensure the installed `quickplace` folder contains `__init__.py`, `plugin.py`, `engine.py`, and `adapter.py`.

No administrator permission, network access, or separate Python installation is needed after downloading either package.

## Use

Open a PCB with a **closed, straight-segment Edge.Cuts outline** and imported footprints. Save a backup first. Click **QuickPlace Now**, leave **Instant** selected, and click **QuickPlace Now** in the dialog to compute and apply after confirmation. Choose **Preview** to see the summary without changing the board, then **Apply** or **Cancel**. Optimize runs bounded local improvement after Instant. Preferences are stored in `%APPDATA%\QuickPlace\settings.json`.

The displayed improvement is a *heuristic sum of net bounding-box spans*, not a routing or DRC result. Run **Inspect → Design Rules Checker** in KiCad after placement and before routing. The legacy Python Action Plugin API does not expose a public undo transaction in KiCad 10.0.6; QuickPlace restores positions if applying raises an exception, but **Undo is not guaranteed**. Save a backup before applying. Locked footprints and footprints connected to routed copper remain fixed. The plugin never changes board sides, tracks, vias, zones, or nets.

## Conservative limitations

QuickPlace rejects board outlines with multiple outer contours, unsupported curved Edge.Cuts geometry, curved existing tracks, complex courtyards, malformed footprints and insufficient space. Missing courtyards use a full footprint bounding rectangle and are listed in warnings. Footprint and track bounding boxes can include text or other geometry and may reject valid layouts. Tracks and vias are obstacles; footprint overlap checks use courtyards when available. Rule-area zones are treated as obstacles on both sides, regardless of individual keepout flags, which is conservative. The current adapter does not prove every possible KiCad DRC condition: custom pad shapes, internal-layer copper, constraints on zone fills, manufacturing clearance, silkscreen and other design-rule checks remain for KiCad's DRC. If these limitations affect your board, do not treat the geometric result as validated. Do not expect a strict wall-clock ceiling: the time budget limits search effort, not validation or KiCad integration.

The planner is deterministic in Instant mode; Optimize uses a fixed random seed and a wall-clock iteration cap. Board geometry is checked in millimetres. No automatic side flipping or moving routed footprints occurs.

## Development

Run unit tests with `python -m unittest discover -s tests -v`. Run real-binding smoke tests using `"C:\Program Files\KiCad\10.0\bin\python.exe" -m unittest discover -s tests -v`. Rebuild the example with the bundled Python: `"C:\Program Files\KiCad\10.0\bin\python.exe" scripts\make_example.py`. Run `python benchmarks\benchmark.py` to print JSON results for 10, 20, 50 and 100 footprints. Rebuild both archives with `python scripts\package.py`. The output `dist/quickplace-pcm.zip` uses the official KiCad PCM archive layout; `dist/quickplace-kicad10.zip` remains the manual scripting-folder archive. The repository root `metadata.json` is the package manifest; the PCM archive includes a copy with no repository-only download hash/URL fields.

The source is separated into `quickplace/engine.py` (pure Python geometry, graph, planner), `quickplace/adapter.py` (KiCad bridge) and `quickplace/plugin.py` (wx interface and registration). The sample board is `examples/quickplace_demo.kicad_pcb`.

## KiCad API references

- [KiCad 10 PCB Editor scripting manual](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#scripting)
- [KiCad legacy pcbnew bindings caveats](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/index.html)
- [KiCad 10 BOARD Python API](https://docs.kicad.org/doxygen-python-10.0/classpcbnew_1_1BOARD.html)
