---
layout: page
title: Philosophy
---

## Draw the problem, not the scaffold

You already know where the scaffold has to go: along these walls, up to this height. Nobody should have to model frames and decks to say that. ScaffVisor takes the faces you select as the whole input and works out the rest.

- **The faces decide the side.** The scaffold stands on the side the face normals point to. One switch (*Flip*) reverses it for courtyards and interiors.
- **The faces decide the height.** Each wall takes its own height from its faces. A fixed height is only used when you start from a curve or edges. An offset lets you stop below the wall top.
- **The wall offset is a number.** The clear distance to the wall is a value in metres, not something you place by eye.

## The ground is part of the model

On a ruin the ground is never flat. The terrain mesh is read directly, every leg is probed onto it, and the scaffold is built from standard parts: 2 m lifts, a compensation frame where needed, threaded jacks within their allowed travel. Decks stay level at heights set by the faces, so a stepped scaffold appears where the ground falls away. Where the terrain asks for more than the jacks allow, you get a note, not a silent error.

## Walkways are free

On the real scaffold you walk and carry loads along the decks. So no mid-height or transverse bar crosses the walkway, and decks are flush with their end fittings, with nothing to trip on. Decks are also not treated as "floor": they hold the structure together, so ScaffVisor lays one at every level and adds a low deck on top of a compensation frame where the ground is high. Edge protection is complete: top rail, mid rail and toeboard. If you do not want toeboards, you can switch them off, and they leave the bill of materials too.

## Numbers you can trace

Every dimension and weight comes from a **preset**, a plain data file, not from the code. Each value carries a source and a flag: *verified* only after somebody weighed or measured the real part. Parts the catalog does not list are computed and marked **estimated**, in the panel and in the export. A system that is not yet checked is labelled as such.

## Honest about what it is

The result is a planning aid: it shows the scaffold, counts the parts and adds up the weight. It does not check stability, wind, loads or ground bearing capacity. Ties and braces follow indicative rules from the manufacturer's documents. The final design and the assembly follow the manufacturer's manual and the person responsible for the site.

## A quiet interface

The panel shows only what the next decision needs. Before a scaffold exists it has three rows and one button. After that, a thin status strip and four sections, with the rarely used settings folded away. Notes are never hidden: their count sits in the strip. Feedback appears next to the control it belongs to, dimmed, so you see the effect of a change without reading a report.
