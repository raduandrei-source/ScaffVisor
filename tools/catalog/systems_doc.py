"""Generate docs/systems.md (catalog of documented scaffold systems, grouped by dimensional family, no duplicates)
and families.json (data for the report). Usage: python systems_doc.py <out dir> <repo dir>"""
import json, os, sys, re, glob, collections

OUT, REPO = sys.argv[1], sys.argv[2]
rows = json.load(open(os.path.join(OUT, "catalog_all.json"), encoding="utf-8"))
presets = {}
for f in glob.glob(os.path.join(REPO, "presets", "*.json")):
    d = json.load(open(f, encoding="utf-8"))
    presets[os.path.basename(f)[:-5]] = d

# (family title, dimensions text, [(catalog row indices merged as one system, preset ids, display override)])
FAM = [
 ("Frame façade", [
  ("Frame 0.73 m, U-deck grid (Layher Blitz type)",
   "Frames 0.73 m wide (axis), 2.00 m lift, compensation frames 0.66 / 1.00 / 1.50 m. Bays 1.57 / 2.07 / 2.57 / 3.07 m (+ 0.73 / 1.09). U-decks 0.32 m (two per bay) or 0.61 m. Tube Ø48.3.",
   [([], ["layher_blitz70_steel"], ("Layher", "Blitz 70 steel", "EU")), ([1], ["layher_blitz70_alu"], None),
    ([7], ["altrad_mostostal_plus70"], ("Altrad Mostostal", "Plus 70", "PL / RO")), ([5], ["scafom_rux_framescaff"], None),
    ([9], ["altrad_assco_quadro70"], None)]),
  ("Frame 1.09 m, U-deck grid (Layher Blitz type)",
   "Same grid, frames 1.09 m: three 0.32 m decks or 0.61 + 0.32 m per bay.",
   [([0], ["layher_blitz100_steel"], None), ([], ["altrad_mostostal_plus100"], ("Altrad Mostostal", "Plus 100", "PL / RO"))]),
  ("Frame 0.74 m (Plettac SL type)",
   "Frames 0.74 m, 2.00 m lift, compensation frames 0.50 / 1.00 / 1.50 m. Bays 1.50 / 2.00 / 2.50 / 3.00 m (+ 0.74 / 1.10, 4.00). Decks 0.32 m on star pins (two per bay) or 0.64 m.",
   [([], ["plettac_sl70"], ("Altrad plettac", "SL 70 steel", "EU")), ([3], ["plettac_sl70_alu"], None), ([8], ["slv_ram2_slv70"], None)]),
  ("Frame 1.10 m (Plettac SL type)", "Same grid, frames 1.10 m, three 0.32 m decks per bay.",
   [([2], ["plettac_sl100_steel"], None)]),
  ("Frame 0.74 m (Hünnebeck BOSTA)",
   "Frames 0.74 m, compensation 0.66 / 1.00 / 1.50 m. Bays 1.25 / 1.50 / 2.00 / 2.50 / 3.00 m (+ 4.00). Decks 0.32 m or 0.70 m alu frame decks; timber toeboards 11 cm.",
   [([4], ["hunnebeck_bosta70_steel"], None), ([11], [], None)]),
  ("Other frame façade systems",
   "Each on its own grid: RUX Super 65 (0.65 m frames, 0.29 m decks), PERI UP T 72/104 and UP Easy (rosette frames 0.67-1.04 m), ERNST (0.80 m trade scaffold), an unnamed 1.0 x 2.0 m access frame.",
   [([10], [], None), ([26], [], None), ([6], [], None), ([12], [], None), ([64], [], None)]),
 ]),
 ("Walk-through frames (US / Asian)", [
  ("Walk-through frame 1.22 x 1.93 m (Asian 4 ft frame)",
   "Frames 1219 mm wide, 1930 mm high (+ 1700 / 1524 / 1219 / 914). Cross braces on both faces of every bay; bays 1829 / 1524 / 1219 / 914 mm. Catwalk 1829 x 500 mm or 210/240 mm planks. The same part is sold by several makers.",
   [([42], ["ab_frame_walkthrough"], None), ([40], [], None), ([41], [], None), ([67], [], None)]),
  ("Walk-through frame 5 ft (US)",
   "Frames 1524 mm (5 ft) wide, 6 ft 4 in - 6 ft 7 in high; cross braces for 5-10 ft bays; timber or steel planks.",
   [([57], [], None), ([53], [], None), ([13], [], None)]),
 ]),
 ("Ringlock / rosette", [
  ("Ringlock 0.73 m, grid 1.57-3.07 m (Layher Allround type)",
   "Rosettes every 0.50 m on Ø48.3 standards; transoms 0.73 / 1.09 m; ledgers 0.73-3.07 m (also 1.40, 4.14). Steel decks 0.32 m (two per 0.73 m bay) or 0.19 m.",
   [([14], [], None), ([34, 24], [], None), ([35], ["coronet_ringlock"], None), ([51], ["apac_ringlock"], None),
]),
  ("Ringlock 0.73 m, imperial bays 5-10 ft", "Same node and 0.73 m transom; ledgers in feet (3-10 ft) as well as metric lengths.",
   [([38], ["dss_ringlock"], None)]),
  ("Ringlock 0.72 m, grid 1.50-3.00 m (PERI UP)",
   "Rosettes every 0.50 m; transoms 0.72 / 1.04 m; ledgers 0.25-4.00 m. Steel decks UDS 32.",
   [([27, 28, 15], ["peri_up_rosett"], ("PERI", "UP Rosett / UP Flex", "EU"))]),
  ("Ringlock, metric round grid (Asian)",
   "Ledgers in round metric lengths (0.65 / 0.7 / 0.9 / 1.0 / 1.2 / 1.4 / 1.5 / 1.8 m ...); dimensions differ between makers.",
   [([43], [], None), ([61], [], None)]),
  ("Ringlock, Plettac grid", "Ledgers 0.74 / 1.10 / 1.50-3.00 m, matching the Plettac SL frames.", [([25], [], None)]),
  ("Other ringlock systems (dimensions not documented here)", "Listed with their maker; tables not found.",
   [([16], [], None), ([17], [], None), ([18], [], None), ([19], [], None), ([20], [], None)]),
 ]),
 ("Cuplock", [
  ("Cuplock 1.25-1.30 m, bays 1.8 / 2.5 m (Cuplok type)",
   "Cups every 0.50 m on Ø48.3 standards; horizontals 1.3 / 1.8 / 2.5 m (also 0.6 / 0.9 / 1.2 / 1.6). Steel planks 0.225-0.23 m (five per 1.3 m) or timber boards.",
   [([56, 22], [], ("SGB (BrandSafway)", "Cuplok", "UK")), ([52], ["apac_cuplock"], None), ([36], ["duscaff_scafflok_plus"], None),
    ([63], [], None), ([44], [], None)]),
  ("Cuplock, imperial bays 5-10 ft", "Same node; horizontals 3-10 ft; 4 ft transom.", [([37], ["dss_cuplock"], None)]),
 ]),
 ("Kwikstage", [
  ("Kwikstage 1.2 m, bays 1.8 / 2.4 m",
   "V-pressings every 0.495 m; transoms 0.7 / 1.2 m; ledgers 0.7 / 1.2 / 1.8 / 2.4 m; steel planks 0.23 m (five per 1.2 m).",
   [([50], ["apac_kwikstage"], None), ([48], ["unispan_kwikstage"], None), ([65], [], None)]),
 ]),
 ("Other modular systems", [
  ("Wedge-lock and other nodes", "Waco Wedgelok (nodes 0.50 m, imperial bays 5-10 ft, 2 ft 6 in transom); HAKI Universal; BWYS C25.",
   [([59], ["waco_wedgelok"], None), ([21], [], None), ([68], [], None)]),
 ]),
 ("Tube and coupler", [
  ("Tube Ø48.3 (EN 74 / BS 1139) and Ø48.6 (JIS), Ø50.8 (US)", "Loose tubes, right-angle and swivel couplers, boards. Not a system grid: ScaffVisor does not build these yet.",
   [([55], [], None), ([49], [], None), ([54], [], None), ([33], [], None), ([66], [], None), ([60], [], None), ([45], [], None), ([47], [], None), ([70], [], None), ([58], [], None)]),
 ]),
 ("Mobile towers", [
  ("Aluminium towers (EN 1004)", "Single and double width towers; not façade scaffolds.", [([46], [], None), ([62], [], None)]),
 ]),
 ("Not access scaffolds", [
  ("Shoring, stairs, girders", "Listed for completeness; outside ScaffVisor's scope.",
   [([29], [], None), ([30], [], None), ([31], [], None), ([32], [], None), ([69], [], None)]),
 ]),
]

CAT = {"frame": "frames", "deck": "decks", "access_deck": "access decks", "diagonal": "diagonals", "guard_rail": "guard rails",
       "toeboard": "toeboards", "end_guard_rail": "end rails", "end_toeboard": "end toeboards", "base_jack": "base jacks",
       "tie": "ties", "coupler": "couplers", "standard": "standards", "ledger": "ledgers", "transom": "transoms",
       "bracket": "brackets", "other": "other parts"}


def short_src(r):
    s = (r.get("sources") or [""])[0] if r else ""
    m = re.search(r"https?://([^/]+)", s)
    if m:
        return m.group(1).replace("www.", "")
    m = re.search(r"([0-9]{6,}-[^ ,;]+?)(\.pdf)?([ ,;]|$)", s)
    return (m.group(1)[:40] if m else s[:40])


MAKERS = [("Wilhelm Layher", "Layher"), ("Altrad plettac assco", "Altrad plettac"), ("Altrad plettac", "Altrad plettac"),
          ("ALTRAD-Mostostal", "Altrad Mostostal"), ("Altrad Mostostal", "Altrad Mostostal"), ("Hünnebeck", "Hünnebeck"),
          ("Scafom-rux", "Scafom-rux"), ("PERI", "PERI"), ("SLV-GROUP", "SLV"), ("Sebastian ERNST", "ERNST"), ("DSS", "DSS"),
          ("Doka", "Doka"), ("Coronet", "Coronet"), ("APAC", "APAC"), ("Duscaff", "Duscaff"), ("Yew Huat", "Yew Huat"),
          ("Grandhome", "Grandhome"), ("A & B", "A & B Scaffold"), ("Uni-span", "Uni-span"), ("SGB", "SGB (BrandSafway)"),
          ("Waco", "Waco"), ("PT. Rendez", "Rendez"), ("Extra Co", "Extra Co (name to confirm)"), ("BWYS", "BWYS"), ("HAKI", "HAKI"),
          ("plettac Distribution", "plettac Distribution"), ("Altrad", "Altrad")]
SYSTEMS = {"Layher Blitz 70 Aluminium": "Blitz 70 aluminium", "Layher Blitz 100 Stahl": "Blitz 100 steel", "assco quadro 70": "assco quadro 70",
           "plettac SL 70 Aluminium": "SL 70 aluminium", "plettac SL 100 Stahl": "SL 100 steel", "BOSTA 70": "BOSTA 70 steel",
           "RUX Super 65": "RUX Super 65 / Super 100", "PERI UP T 72-104 Frame Scaffolding": "UP T 72 / T 104 frame",
           "PERI UP Easy": "UP Easy", "ERNST Fassadengerüst": "Facade scaffold, 0.80 m frames",
           "Access scaffolding frame": "Access frame 1.0 x 2.0 m", "Access Scaffolding": "Walk-through frame",
           "Waco frame scaffold": "Red / Blue walk-through frames", "Frame Access Scaffold System": "Walk-through frame (US style)",
           "DSS frame scaffold, C-size": "C-size / B-size walk-through frames", "Layher Allround": "Allround (steel / aluminium)",
           "Doka Ringlock": "Ringlock", "Coronet Ringlock System": "Ringlock", "Ringlock Access Scaffold System": "Ringlock",
           "DSS Ring Lock": "Ring Lock", "All Around System": "All Around (ringlock)", "Rendez Ringlock": "Ringlock",
           "PDM modular scaffolding": "PDM modular", "Plettac Metrix": "Metrix", "plettac Contur": "Contur",
           "Cuplock Access Scaffold System": "Cuplock", "SCAFFLOK PLUS": "Scafflok Plus", "Cup-lock with steel decking and infill system": "Cup-lock",
           "Cuplock System": "Cuplock", "DSS Cup Lock": "Cup Lock", "Kwikstage Access Scaffold System": "Kwikstage",
           "Scaffolding": "Kwikstage type", "Quick stage": "Quick stage (kwikstage type)", "HAKI Universal": "Universal",
           "BW C25 Modular System": "C25 modular", "Scaffolding Equipment - Tube & Fittings": "Tube and fittings",
           "Scaffold Tube & Fittings": "Tube and fittings", "Tube & Fitting System": "Tube and fittings",
           "PERI UP System-Independent Accessories": "Tube, couplers, ties", "Tube and fitting accessories": "Tube and fittings",
           "Rendez Tubular": "Tube and couplers", "Tubes and Couplers - JIS 3444 / BS 1139": "Tube and couplers (JIS / BS)",
           "Scaffolding Pipes & Fittings": "Pipes and fittings (STK 500)", "BW tube & coupler": "Tube and coupler", "FASTUBE": "Fastube (tube and clamp)",
           "Aluminum Frame Scaffold Tower": "Aluminium tower", "Rendez Aluminium mobile tower": "Aluminium tower",
           "PERI UP Rosett Shoring": "UP Rosett shoring", "PERI UP Scaffold Units": "UP scaffold units", "PERI UP Stairs": "UP stairs",
           "PERI LGS Lattice Girder System": "LGS lattice girder", "BW C60 Shoring System": "C60 shoring", "BW prefabricated steel frame system": "Walk-through frame",
           "Steel Frame Scaffold": "Walk-through frame", "Frame Scaffold": "Walk-through frame", "Ringscaff": "Ringscaff", "MODEX": "MODEX",
           "Futuro": "Futuro", "Wedgelok": "Wedgelok", "FRAMESCAFF": "Framescaff", "BOSTA 100": "BOSTA 100"}


def clean(maker, system):
    maker = maker or ""
    for k, v in MAKERS:
        if maker.startswith(k) or ("DSS" in maker and k == "DSS"):
            maker = v
            break
    base = re.sub(r"\s*\(.*$", "", system or "").strip()
    for k in sorted(SYSTEMS, key=len, reverse=True):
        if base.startswith(k) or (system or "").startswith(k):
            return maker, SYSTEMS[k]
    return maker, base or system


used = set()
fams = []
md = ["---", "layout: page", "title: Scaffold systems", "---", "",
      "Every scaffold system found in the collected documentation and in published manufacturer data, grouped by dimensions. "
      "Systems that share a grid (same widths, bay lengths and lift) are listed together: their parts fit the same layout, "
      "but weights and article numbers differ by maker. A system appears once even if several documents describe it.", "",
      "The [systems catalog](catalog/) has one sheet per system you can pick, with a model, dimensioned views, when to use it and its sources. ",
      "**In ScaffVisor** names the preset you pick in the *System* list. The others are documented here for later presets; "
      "a preset is added only when the parts list with weights is published.", ""]
nsys = nbuilt = 0
for group, families in FAM:
    md += ["## " + group, ""]
    for title, dims, members in families:
        md += ["### " + title, "", dims, "",
               "| Maker | System | Region | In ScaffVisor | Parts with weight | Documented parts | Source |",
               "|---|---|---|---|---|---|---|"]
        fam = dict(group=group, title=title, dims=dims, members=[])
        for idx, pids, over in members:
            rs = [rows[i] for i in idx]
            used.update(idx)
            r0 = rs[0] if rs else None
            maker, system, region = over if over else (r0["manufacturer"], r0["system"], r0.get("region") or "")
            maker, system = clean(maker, system)
            cats = collections.Counter()
            nm = nall = 0
            for r in rs:
                cats.update(r["cats"])
                nm += r["nmass"]
                nall += r["n"]
            for pid in pids:
                if not rs:
                    c = presets[pid]["components"]
                    nm = nall = sum(len(v) if isinstance(v, list) else 1 for v in c.values())
            parts = ", ".join(CAT.get(k, k) for k, _ in cats.most_common() if k != "other") or ("see preset" if pids else "-")
            built = "<br>".join("`%s`" % presets[p]["_meta"]["name"] for p in pids) or "-"
            src = "; ".join(sorted({short_src(r) for r in rs})) or "; ".join(presets[p]["_meta"]["sources"][0][:60] for p in pids)
            region = (region or "").split("(")[0].split(",")[0].strip()[:20]
            md.append("| %s | %s | %s | %s | %s | %s | %s |" % (maker, system, region, built,
                      ("%d / %d" % (nm, nall)) if nall else "-", parts, src))
            fam["members"].append(dict(maker=maker, system=system, region=region, presets=pids, built=[presets[p]["_meta"]["name"] for p in pids],
                                       nmass=nm, n=nall, parts=parts, src=src, sources=[x for r in rs for x in (r.get("sources") or [])]))
            nsys += 1
            nbuilt += 1 if pids else 0
        md.append("")
        fams.append(fam)

missing = [i for i in range(len(rows)) if i not in used and rows[i]["type"] != "modular_other" or (i not in used and "shared" not in (rows[i]["system"] or ""))]
missing = [i for i in range(len(rows)) if i not in used]
md += ["## How to read the table", "",
       "- *Parts with weight*: parts listed with a published weight / all parts listed for that system in the source.",
       "- Imperial systems keep their foot-based bays (5, 6, 7, 8, 10 ft).",
       "- Accessories shared by a maker across its systems (DSS planks, jacks, toeboards) are counted with the presets that use them.", ""]
open(os.path.join(REPO, "docs", "systems.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))
json.dump(dict(families=fams, systems=nsys, built=nbuilt, presets=len(presets), unused=[rows[i]["system"] for i in missing]),
          open(os.path.join(OUT, "families.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("systems", nsys, "built", nbuilt, "presets", len(presets))
print("catalog rows not placed:", [(i, rows[i]["system"]) for i in missing])
