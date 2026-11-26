# Systems catalog tools

Regenerate the catalog (`docs/catalog/`) and the systems page (`docs/systems.md`) after a preset changes.

1. Models and renders (one Blender run per preset; saves `<id>.blend` and `<id>_iso.webp`):
   `blender -b --factory-startup -P bl_catalog_model.py` with the environment variables
   `SVROOT` (folder that contains the add-on folder `scaffvisor`), `PRESET` (preset id), `BLEND_OUT`, `IMG_OUT`.
2. Systems page: `python systems_doc.py <research dir> <repo>` (reads `catalog_all.json`, writes `docs/systems.md` and `families.json`).
3. Catalog page: `python gen_scaff_catalog.py <repo> <families.json> catalog.css <render dir>`.

`catalog.css` is the stylesheet of the CutVisor joints catalog (same fonts, colours and sheet layout).
`validate_preset.py <preset.json>` runs the engine checks on one preset.
`build_presets.py` rebuilt the frame-system presets from the sourced research tables (kept for reference: later
edits to the presets, such as families and source links, were made in the JSON files).
The research tables with sources are kept with the project files (`CERCETARE ARH/ScaffVisor/catalog/research/`).
