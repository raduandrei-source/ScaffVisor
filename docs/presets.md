---
layout: page
title: Systems and presets
---

A scaffold system is a data file in the add-on's `presets` folder. The code contains no dimension or weight of any manufacturer.

## Built in

23 systems. Each has a sheet with a model, dimensioned views and its sources in the [systems catalog](catalog/); the [systems page](systems.html) lists every system found in the documentation.

| System | Type | Grid | Status |
|---|---|---|---|
| Altrad Mostostal Plus 70 (steel, 73 cm) | frame | Frame 0.73 m, U-deck grid 1.57-3.07 m (Layher Blitz type) | Values from the published parts list; some parts estimated (marked *) |
| Altrad assco quadro 70 (steel, 73 cm) | frame | Frame 0.73 m, U-deck grid 1.57-3.07 m (Layher Blitz type) | Values from the published parts list; some parts estimated (marked *) |
| Layher Blitz 70 (aluminium, 73 cm) | frame | Frame 0.73 m, U-deck grid 1.57-3.07 m (Layher Blitz type) | Values from the published parts list; some parts estimated (marked *) |
| Layher Blitz 70 (steel, 73 cm) | frame | Frame 0.73 m, U-deck grid 1.57-3.07 m (Layher Blitz type) | Values from the published parts list; some parts estimated (marked *) |
| Scafom-rux Framescaff (steel, 73 cm) | frame | Frame 0.73 m, U-deck grid 1.57-3.07 m (Layher Blitz type) | Values from the published parts list; some parts estimated (marked *) |
| Hünnebeck BOSTA 70 (steel, 74 cm) | frame | Frame 0.74 m, grid 1.25-3.00 m (Hünnebeck BOSTA) | Values from the published parts list; some parts estimated (marked *) |
| Plettac SL 70 (aluminium, 74 cm) | frame | Frame 0.74 m, grid 1.50-3.00 m (Plettac SL type) | Values from the published parts list; some parts estimated (marked *) |
| Plettac SL 70 (steel, 74 cm) | frame | Frame 0.74 m, grid 1.50-3.00 m (Plettac SL type) | Values from the manufacturer's catalog (ed. 04/2013). Checked against its example of 123 m and 3 lifts: 126 frames, 84 jacks, 27 braces, about 10.7 t |
| SLV RAM 2 / SLV 70 (steel, 74 cm) | frame | Frame 0.74 m, grid 1.50-3.00 m (Plettac SL type) | Values from the published parts list |
| Altrad Mostostal Plus 100 (steel, 109 cm) | frame | Frame 1.09 m, U-deck grid 1.57-3.07 m (Layher Blitz type) | Values from the published parts list; some parts estimated (marked *) |
| Layher Blitz 100 (steel, 109 cm) | frame | Frame 1.09 m, U-deck grid 1.57-3.07 m (Layher Blitz type) | Values from the published parts list; some parts estimated (marked *) |
| Plettac SL 100 (steel, 110 cm) | frame | Frame 1.10 m, grid 1.50-3.00 m (Plettac SL type) | Values from the published parts list |
| A & B walk-through frame (steel, 122 cm) | frame | Walk-through frame 1.22 x 1.93 m, bay 1.83 m (Asian 4 ft frame) | Values from the published parts list; some parts estimated (marked *) |
| DSS Cup Lock (steel, 122 cm, imperial bays) | modular | Cuplock 1.22 m, imperial bays 5-10 ft (node 0.50 m) | Values from the published parts list; some parts estimated (marked *) |
| APAC Cuplock (steel, 125 cm) | modular | Cuplock 1.25-1.30 m, bays 1.8 / 2.5 m (Cuplok type, node 0.50 m) | Values from the published parts list; some parts estimated (marked *) |
| Duscaff Scafflok Plus (steel, 130 cm) | modular | Cuplock 1.25-1.30 m, bays 1.8 / 2.5 m (Cuplok type, node 0.50 m) | Values from the published parts list; some parts estimated (marked *) |
| APAC Kwikstage (steel, 120 cm) | modular | Kwikstage 1.2 m, bays 1.8 / 2.4 m (node 0.495 m) | Values from the published parts list; some parts estimated (marked *) |
| Uni-span Kwikstage type (steel, 120 cm) | modular | Kwikstage 1.2 m, bays 1.8 / 2.4 m (node 0.495 m) | Values from the published parts list; some parts estimated (marked *) |
| PERI UP Rosett (steel, 72 cm) | modular | Ringlock 0.72 m, grid 1.50-3.00 m (PERI UP, node 0.50 m) | Values from the published parts list |
| APAC Ringlock (steel, 73 cm) | modular | Ringlock 0.73 m, grid 1.57-3.07 m (Layher Allround type, node 0.50 m) | Values from the published parts list; some parts estimated (marked *) |
| Coronet Ringlock (steel, 73 cm) | modular | Ringlock 0.73 m, grid 1.57-3.07 m (Layher Allround type, node 0.50 m) | Values from the published parts list; some parts estimated (marked *) |
| DSS Ring Lock (steel, 73 cm, imperial bays) | modular | Ringlock 0.73 m, imperial bays 5-10 ft (node 0.50 m) | Values from the published parts list; some parts estimated (marked *) |
| Waco Wedgelok (steel, 76 cm, imperial bays) | modular | Wedge-lock 0.76 m, imperial bays 5-10 ft (Waco) | Values from the published parts list; some parts estimated (marked *) |

*Frame* systems are built from frames, decks and diagonals. *Modular* systems (ringlock, cuplock, kwikstage, wedge-lock) are counted as standards, ledgers, transoms and base collars; in the viewport they are drawn with the same silhouette as a frame (two standards and a transom per lift).

Rules a source does not give (tie area, wall gap) use placeholder values; each preset says which in `rules_verified`, and the catalog sheet repeats it.

More systems are added only from published technical data. Each one lists its sources.

## How values are marked

- **verified**: weighed or measured on the real part. Until then the flag is false, whatever the catalog says. Clones of a system may differ slightly from the original.
- **estimated**: the catalog does not list the part, so the add-on computes it, for example a diagonal for a lift height that has no catalog entry. Estimated weights are flagged in the panel (a star in the parts list) and in the export.
- **sources**: each preset names the documents it came from.

## What a preset contains

- the system: frame width and height, tube diameter, bay lengths, deck width and number of decks per bay, compensation frame heights;
- the components: frames (or standards, ledgers and transoms for a modular system), decks, access decks with ladder and hatch, diagonals, guard rails, toeboards, jacks, ties, with article numbers and weights;
- the rules: ties per area, free height above a tie, braces every few bays, jack extension limits, wall gap limits;
- a sanity check: a catalog example the result is compared against.

## Adding your own

Copy an existing file in `presets/`, change the values, keep the structure, and restart the add-on. It appears in the **System** list. Start from the catalog of your system and fill in the *sources* field.

A friendlier preset manager and CSV import from supplier lists are planned.
