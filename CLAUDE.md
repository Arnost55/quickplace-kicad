# QuickPlace project instructions

## Project scope

QuickPlace is an offline KiCad 10 PCB Editor Action Plugin. Preserve separation between the pure-Python planner (`quickplace/engine.py`), `pcbnew` bridge (`quickplace/adapter.py`), and UI/action registration (`quickplace/plugin.py`). Do not add cloud services, API keys, or runtime dependencies without a clear requirement.

## Safety requirements

- Never modify schematic/netlist connectivity, tracks, vias, zones, or board side assignments.
- Treat locked footprints and footprints connected to existing routed copper as fixed.
- Fail without applying if board outline, geometry or obstacle constraints cannot be checked safely.
- Compute and validate the entire proposal before applying any position changes. Preserve original positions and restore them if application fails.
- Do not claim DRC validity or guaranteed KiCad undo support. The KiCad 10.0.6 legacy `pcbnew` Python binding has no exposed public undo transaction; tell users to save a backup before applying and run DRC afterwards.
- Document any conservative rejection, approximation, or unsupported geometry rather than silently weakening validation.

## Development and validation

Use only documented/verified KiCad 10 stable `pcbnew` APIs, and check behavior against the installed KiCad bundled Python when possible. Keep planner tests runnable under ordinary Python with no third-party dependencies.

Run both test suites when KiCad 10 is installed:

```bash
python -m unittest discover -s tests -v
"C:\Program Files\KiCad\10.0\bin\python.exe" -m unittest discover -s tests -v
```

Run synthetic benchmarks with `python benchmarks/benchmark.py`. Report measured figures without implying that performance targets were met when they were not. Regenerate the example board with KiCad's bundled Python and rebuild archives with `python scripts/package.py`.

## Packaging

- Keep the manual Action Plugin ZIP (`dist/quickplace-kicad10.zip`) and KiCad PCM package (`dist/quickplace-pcm.zip`) distinct.
- The PCM archive must have `metadata.json` at the archive root, plugin files directly under `plugins/`, and its optional PCM icon under `resources/icon.png`.
- Keep `metadata.json` conforming to the KiCad PCM v2 schema. Repository-only `download_*` values must not be copied into the archive's own manifest.
- Verify archive members and integrity after packaging. A GitHub repository URL is not itself a PCM repository index; document Install from File or the need for a separately configured/approved repository listing.

## Git workflow

After each coherent change, review the diff, run relevant checks, stage only related files, and create a focused local commit. Preserve unrelated working-tree changes. Do not force-push, rewrite history, merge, deploy or publish additional external changes unless explicitly requested. Push only when the user asks.
