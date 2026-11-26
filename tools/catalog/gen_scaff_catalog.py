"""ScaffVisor scaffold-systems catalog (same look as the CutVisor joints catalog).
Usage: python gen_scaff_catalog.py <repo> <families.json> <joints catalog.css> <iso image dir>
Writes <repo>/docs/catalog/index.html and copies the isometric renders to <repo>/docs/catalog/img/."""
import html, json, math, os, re, shutil, sys

REPO, FAMJ, CSSF, ISO = sys.argv[1:5]
sys.path.insert(0, REPO)
from core.preset import load_preset, list_presets  # noqa: E402
from core.layout import build_plan  # noqa: E402
from core.rules import apply_rules  # noqa: E402
from core.bom import compute_bom  # noqa: E402

OUT = os.path.join(REPO, "docs", "catalog")
os.makedirs(os.path.join(OUT, "img"), exist_ok=True)
E = lambda s: html.escape(str(s), quote=True)
VERSION = "0.6.0"
FAMS = json.load(open(FAMJ, encoding="utf-8"))["families"]

# --------------------------------------------------------------- links for sources
SCRIBD = re.compile(r"\b(\d{8,10})-([A-Za-z0-9][\w\-]*)")
URL = re.compile(r"https?://[^\s,;)]+")
BARE = re.compile(r"\b((?:www\.)?[a-z0-9\-]+\.(?:de|ua|ee|fi|pl|com|ro|co\.uk|uk|org|net|sg|au)/[^\s,;)]+)")


def linkify(src):
    """Source text with every reference turned into a web link: URLs, bare domain paths, and the
    Scribd documents of the 'documentare' folder (file names start with the Scribd document number)."""
    out, pos = [], 0
    spans = []
    for m in URL.finditer(src):
        spans.append((m.start(), m.end(), m.group(0).rstrip(".")))
    for m in BARE.finditer(src):
        if not any(a <= m.start() < b for a, b, _ in spans):
            spans.append((m.start(), m.end(), "https://" + m.group(1).rstrip(".")))
    for m in SCRIBD.finditer(src):
        if not any(a <= m.start() < b for a, b, _ in spans):
            slug = re.sub(r"-pdf$", "", m.group(2))
            end = m.end() + (4 if src[m.end():m.end() + 4] == ".pdf" else 0)
            spans.append((m.start(), end, "https://www.scribd.com/document/%s/%s" % (m.group(1), slug)))
    spans.sort()
    for a, b, url in spans:
        if a < pos:
            continue
        out.append(E(src[pos:a]))
        dom = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        label = src[a:b]
        if "scribd.com" in url:
            label = "Scribd " + label.split("-")[0]
        elif len(label) > 48:
            label = dom
        out.append('<a class="ext" href="%s" target="_blank" rel="noopener">%s</a>' % (E(url), E(label)))
        pos = b
    out.append(E(src[pos:]))
    return "".join(out), bool(spans)


# --------------------------------------------------------------- texts per family type (common practice, not a structural assessment)
TXT = {
 "frame": dict(
  adv=["Few part types: frames, decks, rails, diagonals. Quick to erect and to count.",
       "Light per square metre of façade; the decks also brace the frames.",
       "Widely stocked for hire in Europe; clones of the same grid fit together."],
  dis=["Fixed 2.00 m lift and a fixed bay grid; the top deck height comes in steps.",
       "Corners, curves and set-backs need tube-and-coupler additions.",
       "One platform width per frame (0.73-0.74 m, or 1.09-1.10 m for the wide frames)."],
  use=["Straight façades: renovation, painting, render, insulation, restoration of regular walls.",
       "Façades within the manufacturer's standard configuration (typically up to 24 m)."],
  no=["Irregular plans, round towers, roofs and free-standing structures.",
       "Heavy loads beyond the deck's load class; walls that cannot take ties."]),
 "frame_wide": dict(
  adv=["Platform about 1 m wide (W09): room to work and to store material.",
       "Same decks, rails and diagonals as the narrow frames of the system."],
  dis=["Heavier per square metre; wider footprint on the pavement.",
       "Fewer compensation frames in some systems."],
  use=["Masonry, plastering and stone work where material is stored on the deck."],
  no=["Narrow sidewalks or courtyards; light finishing work where 0.73 m is enough."]),
 "walk": dict(
  adv=["Wide frames you can walk through; simple pin-together erection.",
       "Common for building work and interior access in the US and Asia."],
  dis=["Cross braces on both faces of every bay: heavy per square metre and in the way at the inner face.",
       "Imperial or local sizes; planks, guard rails and toeboards are separate items.",
       "Side protection to EN 12811 needs extra rails (cross braces are not guard rails)."],
  use=["Markets where the system is stocked; birdcage and interior access; short façades."],
  no=["European façade work to EN 12811 without additional side protection."]),
 "ringlock": dict(
  adv=["Rosette every 0.50 m with eight holes: ledgers at any level and at 45° steps, so any plan shape.",
       "Same parts make façades, birdcages, stair towers, temporary roofs and supports.",
       "Start heights in 0.50 m steps follow sloping ground."],
  dis=["More pieces than a frame system and heavier per square metre.",
       "Slower to erect on a simple straight façade."],
  use=["Complex or curved façades, churches and listed buildings, industry, corners and set-backs."],
  no=["Long simple façades where a frame system is cheaper and faster."]),
 "cuplock": dict(
  adv=["No loose wedges or couplers: up to four ledgers locked by one cup.",
       "Robust and suited to heavy duty and to shoring."],
  dis=["Only right-angle connections at a node; angled plans need couplers.",
       "Heavy; planks are laid on the transoms and are a separate item."],
  use=["Heavy-duty access, civil works, industry and load-bearing birdcages."],
  no=["Light finishing work on regular façades; plans with many angles."]),
 "kwikstage": dict(
  adv=["Very fast wedge (V-pressing) connections; few loose parts.",
       "Standard system in Australia, New Zealand and parts of the UK."],
  dis=["0.495 m node pitch: not compatible with ringlock or cuplock.",
       "Wide transoms and steel planks: heavy per square metre."],
  use=["Residential and commercial work where the system is stocked."],
  no=["Markets without hire stock; angled plans."]),
 "wedge": dict(
  adv=["Wedge connection without loose couplers; parts in imperial sizes."],
  dis=["Limited availability outside North America; imperial grid."],
  use=["Industrial access in markets where the system is stocked."],
  no=["European projects (no local stock, no EN approval found)."]),
}


def texts_for(pid, p):
    k = p.kind
    fam = p.data["_meta"].get("family", "")
    if "Walk-through" in fam:
        return TXT["walk"]
    if k == "frame":
        return TXT["frame_wide"] if p.width >= 1.0 else TXT["frame"]
    if "Ringlock" in fam:
        return TXT["ringlock"]
    if "Cuplock" in fam:
        return TXT["cuplock"]
    if "Kwikstage" in fam:
        return TXT["kwikstage"]
    return TXT["wedge"]


# --------------------------------------------------------------- 2D views (inline SVG, theme-aware classes of the joints catalog)
def tube(a, b, w, cls):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    return '<polygon class="%s" points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f"/>' % (
        cls, a[0] + nx, a[1] + ny, b[0] + nx, b[1] + ny, b[0] - nx, b[1] - ny, a[0] - nx, a[1] - ny)


def dim(x0, y0, x1, y1, label, off=0, vert=False):
    s = ['<g class="dim st-sursa">', '<line class="dl" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (x0, y0, x1, y1)]
    for (x, y) in ((x0, y0), (x1, y1)):
        if vert:
            s.append('<line class="ext" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (x - 6, y, x + 6, y))
        else:
            s.append('<line class="ext" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (x, y - 6, x, y + 6))
        s.append('<line class="tick" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (x - 3.5, y + 3.5, x + 3.5, y - 3.5))
    if vert:
        cx, cy = x0 - 7 + off, (y0 + y1) / 2
        s.append('<text class="dimtxt" x="%.1f" y="%.1f" text-anchor="middle" transform="rotate(-90 %.1f %.1f)">%s</text>' % (cx, cy, cx, cy, E(label)))
    else:
        s.append('<text class="dimtxt" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % ((x0 + x1) / 2, y0 - 7 + off, E(label)))
    s.append("</g>")
    return "".join(s)


def note(x, y, t, anchor="start"):
    return '<text class="vnote" x="%.1f" y="%.1f" text-anchor="%s">%s</text>' % (x, y, anchor, E(t))


def views(p):
    s = p.data["system"]
    W, H = p.leg_span * 1000, p.frame_h * 1000
    od = s["tube_od_mm"]
    bays = sorted(p.bays_std)
    bay = min(bays, key=lambda b: abs(b - 2500))
    nd, dw = p.decks_per_bay, s["deck_module_width_mm"]
    node = s.get("node_spacing_mm", 0)
    emin, emax = p.rules["jack_ext_min_m"] * 1000, p.jack_emax() * 1000
    ext, gap = 300.0, 150.0
    toe = 110.0 if "11 cm" in p.label("toeboard", "") else 150.0
    walk = p.rules.get("brace_faces", 1) == 2
    top = p.rules.get("top_post_m", 1.0) * 1000
    zd = [ext + H, ext + 2 * H]
    ztop = zd[-1] + top
    sc = 0.075
    tw = max(2.2, od * sc)
    # elevation
    pad_l, pad_b, pad_t = 112, 50, 26
    Wv = 2 * bay * sc + pad_l + 70
    Hv = ztop * sc + pad_b + pad_t
    X = lambda x: pad_l + x * sc
    Y = lambda z: Hv - pad_b - z * sc
    g = ['<svg class="v2d" viewBox="0 0 %.0f %.0f" width="%.0f" height="%.0f">' % (Wv, Hv, Wv, Hv)]
    g.append('<line class="vis" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (X(-300), Y(0), X(2 * bay + 300), Y(0)))
    for i in range(2):
        x0, x1 = i * bay, (i + 1) * bay
        for z in zd:
            g.append(tube((X(x0), Y(z + toe / 2)), (X(x1), Y(z + toe / 2)), toe * sc, "f-A"))
            for dz in (500, 1000):
                g.append(tube((X(x0), Y(z + dz)), (X(x1), Y(z + dz)), tw * 0.8, "f-B"))
        for li in range(2):
            za, zb = ext + H * li, ext + H * (li + 1)
            if walk:
                g.append(tube((X(x0), Y(za + 150)), (X(x1), Y(zb - 150)), tw * 0.6, "f-aux"))
                g.append(tube((X(x0), Y(zb - 150)), (X(x1), Y(za + 150)), tw * 0.6, "f-aux"))
            elif i == 0:
                g.append(tube((X(x0), Y(za + 100)), (X(x1), Y(zb - 100)), tw * 0.6, "f-aux"))
    for i in range(3):
        x = i * bay
        g.append(tube((X(x), Y(0)), (X(x), Y(ext)), tw * 0.7, "f-aux"))
        g.append(tube((X(x), Y(ext)), (X(x), Y(ztop)), tw, "f-C"))
        if p.kind == "frame":
            for z in zd:
                g.append(tube((X(x) - 3, Y(z)), (X(x) + 3, Y(z)), tw, "f-C"))
        if node:
            z = ext + node / 2
            while z < ztop - 20:
                g.append('<circle class="f-C" cx="%.1f" cy="%.1f" r="%.1f"/>' % (X(x), Y(z), tw * 0.9))
                z += node
    g.append(dim(X(0), Y(0) + 26, X(bay), Y(0) + 26, "%.2f" % (bay / 1000), off=0))
    g.append(dim(X(-38), Y(ext), X(-38), Y(zd[0]), "%.2f" % (H / 1000), vert=True))
    g.append(dim(X(-38), Y(zd[0]), X(-38), Y(zd[1]), "%.2f" % (H / 1000), vert=True))
    g.append(dim(X(2 * bay) + 34, Y(zd[1]), X(2 * bay) + 34, Y(zd[1] + 1000), "1.00", vert=True, off=24))
    g.append(note(X(-14), Y(ext / 2) + 4, "jack %.2f-%.2f" % (emin / 1000, emax / 1000), "end"))
    if node:
        g.append(note(X(bay) + 6, Y(ztop) + 12, "nodes every %.3f" % (node / 1000)))
    g.append("</svg>")
    elev = "".join(g)
    # section
    yi = gap + od / 2
    yo = yi + W
    Ws = (yo + 450) * sc + 70
    Xs = lambda y: 40 + y * sc
    g = ['<svg class="v2d" viewBox="0 0 %.0f %.0f" width="%.0f" height="%.0f">' % (Ws, Hv, Ws, Hv)]
    g.append('<rect x="0" y="%.1f" width="%.1f" height="%.1f" fill="var(--grid)"/>' % (Y(ztop + 200), Xs(0), (ztop + 200) * sc))
    g.append('<line class="vis" x1="0" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (Y(0), Ws, Y(0)))
    for y in (yi, yo):
        g.append(tube((Xs(y), Y(0)), (Xs(y), Y(ext)), tw * 0.7, "f-aux"))
        g.append(tube((Xs(y), Y(ext)), (Xs(y), Y(ztop if y == yo else zd[-1] + (top if p.kind == "modular" else 0))), tw, "f-C"))
    used = nd * dw
    y0 = yi + (W - used) / 2
    for z in zd:
        g.append(tube((Xs(yi), Y(z)), (Xs(yo), Y(z)), tw, "f-C"))
        for k in range(nd):
            g.append('<rect class="f-A" x="%.1f" y="%.1f" width="%.1f" height="5"/>' % (Xs(y0 + k * dw) + 0.6, Y(z) - 5.5, dw * sc - 1.2))
        for dz in (500, 1000):
            g.append('<circle class="f-B" cx="%.1f" cy="%.1f" r="%.1f"/>' % (Xs(yo) + tw, Y(z + dz), tw * 0.8))
        g.append('<rect class="f-A" x="%.1f" y="%.1f" width="3" height="%.1f"/>' % (Xs(yo) + tw * 0.6, Y(z + toe), toe * sc))
    g.append(tube((Xs(0), Y(zd[0] - 250)), (Xs(yi), Y(zd[0] - 250)), tw * 0.6, "f-aux"))
    g.append(note(Xs(yi / 2), Y(zd[0] - 250) + 14, "tie", "middle"))
    g.append(dim(Xs(yi), Y(ztop) - 12, Xs(yo), Y(ztop) - 12, "%.2f" % (W / 1000)))
    g.append(dim(Xs(0), Y(zd[1]) + 30, Xs(gap), Y(zd[1]) + 30, ""))
    g.append(note(Xs(gap) + 4, Y(zd[1]) + 34, "gap %.2f" % (gap / 1000)))
    g.append(note(Xs(yo) + 12, Y(zd[0]) + 4, "%d x %.2f" % (nd, dw / 1000)))
    g.append("</svg>")
    return elev, "".join(g)


# --------------------------------------------------------------- per-preset data
def ref_bom(p):
    P = build_plan([(0, 0), (30, 0)], False, p, 2 * p.frame_h + 0.3, gap=0.15, allow_short=False)
    apply_rules(P, p)
    return compute_bom(P, p, deck_grade=p.default_grade())


def parts_rows(p):
    c, rows = p.c, []
    def add(group, code, desc, mass, est=False):
        rows.append((group, code, desc, mass, est))
    if p.kind == "frame":
        for t in sorted(c["frame"]["steel_light_74"], key=lambda t: -t["h_mm"]):
            add("Frames", t["id"], "Frame %.2f x %.2f m" % (t["h_mm"] / 1000, p.leg_span), t["mass"], t.get("estimated", False))
    else:
        for t in sorted(c["standard"], key=lambda t: -t["l_mm"]):
            add("Standards", t["id"], "Standard %.2f m" % (t["l_mm"] / 1000), t["mass"], t.get("estimated", False))
        if c.get("base_collar"):
            add("Standards", c["base_collar"]["id"], p.label("base_collar", "Base collar"), c["base_collar"]["mass"], c["base_collar"].get("estimated", False))
        t = c["transom"]
        add("Ledgers", t["id"], "Transom %.2f m" % (t["l_mm"] / 1000), t["mass"], t.get("estimated", False))
        for t in c["ledger"]:
            if t["l_mm"] in p.bays_std or t["l_mm"] in p.bays_extra:
                add("Ledgers", t["id"], "Ledger %.2f m" % (t["l_mm"] / 1000), t["mass"], t.get("estimated", False))
    g = p.default_grade()
    for t in c["timber_deck_w320"][g]:
        if t["l_mm"] in p.bays_std or t["l_mm"] in p.bays_extra:
            add("Decks", t["id"], p.grade_label(g) + ", %.2f m" % (t["l_mm"] / 1000), t["mass"], t.get("estimated", False))
    for t in c["access_deck_with_ladder_w640"]:
        add("Decks", t["id"], p.label("access", "Access deck") + " %.2f m (%s)" % (t["l_mm"] / 1000, t["surface"]), t["mass"], t.get("estimated", False))
    for t in c["vertical_brace"]:
        add("Bracing", t["id"], "Diagonal, bay %.2f x %.2f m" % (t["bay_mm"] / 1000, t["h_mm"] / 1000), t["mass"], t.get("estimated", False))
    if p.kind == "frame":
        for t in c["guard_rail"]:
            if t["l_mm"] in p.bays_std or t["l_mm"] in p.bays_extra:
                add("Protection", t["id"], "Guard rail %.2f m" % (t["l_mm"] / 1000), t["mass"], t.get("estimated", False))
    for t in c["toeboard_timber_h150"]:
        if t["l_mm"] in p.bays_std or t["l_mm"] in p.bays_extra:
            add("Protection", t["id"], p.label("toeboard", "Toeboard") + " %.2f m" % (t["l_mm"] / 1000), t["mass"], t.get("estimated", False))
    er = c["double_end_guard_rail_74"]
    add("Protection", er["id"], p.label("end_rail", "End guard rail"), er["mass"], er.get("estimated", False))
    et = c["end_toeboard_74"]
    add("Protection", et["id"], p.label("end_toeboard", "End toeboard"), et["mass"], et.get("estimated", False))
    sup = (c.get("top_level") or {}).get("steel_guard_rail_support_h1000_w740")
    if sup and p.kind == "frame":
        add("Protection", sup["id"], p.label("support", "Top guard rail support"), sup["mass"], sup.get("estimated", False))
    for t in c["base_plate_threaded"]:
        ext = (" , extension up to %.2f m" % (p.jack_max_ext(t))) if t else ""
        add("Base", t["id"], "Base jack %.2f m%s" % (t["h_mm"] / 1000, ext.replace(" ,", ",")), t["mass"], t.get("estimated", False))
    ti = c["ties"]
    add("Ties", ti["scaffold_tie_80"]["id"], p.label("tie", "Wall tie"), ti["scaffold_tie_80"]["mass"], ti["scaffold_tie_80"].get("estimated", False))
    add("Ties", ti["normal_coupler"]["id"], p.label("coupler", "Coupler"), ti["normal_coupler"]["mass"], ti["normal_coupler"].get("estimated", False))
    add("Ties", ti["eyebolt_120"]["id"], p.label("eyebolt", "Eye bolt"), ti["eyebolt_120"]["mass"], ti["eyebolt_120"].get("estimated", False))
    return rows


def ul(items):
    return "<ul>" + "".join("<li>%s</li>" % E(t) for t in items) + "</ul>"


# --------------------------------------------------------------- page
cards, toc = [], []
order = []
for fam in FAMS:
    for m in fam["members"]:
        for pid in m["presets"]:
            if pid not in order:
                order.append(pid)
groups = []
for fam in FAMS:
    pids = [pid for m in fam["members"] for pid in m["presets"]]
    if pids:
        groups.append((fam["group"], fam["title"], fam["dims"], list(dict.fromkeys(pids))))

n = 0
sections = []
SEARCH = []
for gi, (grp, ftitle, fdims, pids) in enumerate(groups):
    inner = []
    tlinks = []
    for pid in pids:
        n += 1
        num = "S%02d" % n
        p = load_preset(pid)
        meta, sy = p.data["_meta"], p.data["system"]
        B = ref_bom(p)
        t = texts_for(pid, p)
        src_html = []
        any_link = False
        for s_ in meta.get("sources", []):
            h, ok = linkify(s_)
            any_link |= ok
            src_html.append(h)
        appr = "; ".join(meta.get("approvals", [])) or "none stated in the sources"
        iso = pid + "_iso.webp" if os.path.exists(os.path.join(ISO, pid + "_iso.webp")) else pid + "_iso.png"
        if os.path.exists(os.path.join(ISO, iso)):
            shutil.copy2(os.path.join(ISO, iso), os.path.join(OUT, "img", iso))
        elev, sect = views(p)
        kind_txt = "Frame façade" if p.kind == "frame" else "Modular"
        if "Walk-through" in meta.get("family", ""):
            kind_txt = "Walk-through frame"
        bays_txt = ", ".join("%.2f" % (b / 1000) for b in sorted(p.bays_std)) + (
            " (+ " + ", ".join("%.2f" % (b / 1000) for b in sorted(p.bays_extra)) + ")" if p.bays_extra else "") + " m"
        jacks = ", ".join("%.2f m" % (j["h_mm"] / 1000) for j in p.c["base_plate_threaded"])
        ess = [("Width (leg axes)", "%.2f m" % p.leg_span), ("Lift", "%.2f m" % p.frame_h), ("Bays", bays_txt),
               ("Decks per bay", "%d x %.2f m" % (p.decks_per_bay, sy["deck_module_width_mm"] / 1000))]
        if p.node_spacing:
            ess.append(("Node spacing", "%.3f m" % p.node_spacing))
        ess += [("Base steps", ", ".join("%.2f" % c for c in p.comp_frames) + " m " + ("compensation frames" if p.kind == "frame" else "start heights")),
                ("Base jacks", jacks + "; extension %.2f-%.2f m" % (p.rules["jack_ext_min_m"], p.jack_emax())),
                ("Load class", str(sy.get("load_classes_note") or sy.get("max_load_class", "-"))),
                ("Approvals", appr),
                ("Weight", "%.1f kg/m² on a 30 m wall, 2 lifts (%.0f kg, of which %.0f kg estimated)" % (B["kg_m2"], B["total_kg"], B["est_kg"]))]
        rows = parts_rows(p)
        trs = []
        last = None
        for grp_, code, desc, mass, est in rows:
            trs.append("<tr><th>%s</th><td>%s<span class=\"src\">%s</span></td><td class=\"num\">%s%s</td></tr>" % (
                E(grp_) if grp_ != last else "", E(desc), E(code), ("%.2f kg" % mass), " *" if est else ""))
            last = grp_
        notes = meta.get("changes", [])
        rv = p.rules.get("rules_verified", {})
        rnote = rv.get("note") if isinstance(rv, dict) else ""
        first_src = src_html[0] if src_html else "no source"
        more = ""
        if len(src_html) > 1:
            more = ('<details class="src-more"><summary><span class="sm-o">All sources (%d)</span><span class="sm-c">Hide</span></summary><ol>%s</ol></details>'
                    % (len(src_html), "".join("<li>%s</li>" % h for h in src_html)))
        inner.append(f'''
<article class="sheet" id="{pid}">
  <header class="cartouche">
    <div class="cell num"><span class="k">No.</span><span class="v">{num}</span></div>
    <div class="cell name"><span class="k">{E(kind_txt)}</span><h3>{E(meta["name"])}</h3><p class="alias">{E(meta.get("family", ""))}</p></div>
    <div class="cell"><span class="k">Preset</span><span class="v small">{E(pid)}<br>{E(pid)}.blend</span></div>
    <div class="cell"><span class="k">Sources</span><div class="v small srcbox"><span class="src-first">{first_src}</span>{more}</div></div>
  </header>
  <div class="figs">
    <div class="iso-row">
      <figure class="iso"><div class="iso-pic" style="aspect-ratio:1100/864"><img src="img/{E(iso)}" alt="{E(meta["name"])}, two bays and two lifts on a test façade" loading="lazy"></div>
        <figcaption>Axonometric · 2 bays x 2 lifts · built by ScaffVisor</figcaption></figure>
      <div class="ortho-row" tabindex="0" aria-label="Views">
        <figure class="ortho">{elev}<figcaption>Elevation, outer face</figcaption></figure>
        <figure class="ortho">{sect}<figcaption>Section</figcaption></figure>
      </div>
    </div>
    <p class="figcap">Dimensions in metres, from the preset. Pink tones: structure, decks, rails, braces and jacks.</p>
  </div>
  <div class="body">
    <dl class="facts">
      <div class="fact"><dt>Advantages</dt><dd>{ul(t["adv"])}</dd></div>
      <div class="fact"><dt>Disadvantages</dt><dd>{ul(t["dis"])}</dd></div>
      <div class="fact"><dt>When to use</dt><dd>{ul(t["use"])}</dd></div>
      <div class="fact"><dt>When not to use</dt><dd>{ul(t["no"])}</dd></div>
    </dl>
    <div class="steps"><h4>Essential information</h4>
      <table class="ess"><tbody>{"".join("<tr><th>%s</th><td>%s</td></tr>" % (E(k), E(v)) for k, v in ess)}</tbody></table>
    </div>
  </div>
  <div class="params"><h4>Parts and weights</h4>
    <div class="tablewrap"><table><thead><tr><th>Group</th><th>Part · code</th><th>Weight</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>
    <p class="cnote">* estimated: not in the published list; see the notes. All weights are guideline values from the sources; not weighed on real parts.</p>
    {"<p class='cnote'><b>Rules:</b> " + E(rnote) + "</p>" if rnote else ""}
    {"<details class='src-more'><summary><span class='sm-o'>Notes (" + str(len(notes)) + ")</span><span class='sm-c'>Hide notes</span></summary><ol>" + "".join("<li>%s</li>" % E(x) for x in notes) + "</ol></details>" if notes else ""}
  </div>
</article>''')
        tlinks.append('<a href="#%s" data-id="%s"><span class="ix-n">%s</span><span>%s</span></a>' % (pid, pid, num, E(meta["name"])))
        stext = " ".join([num, kind_txt, meta.get("family", ""), ftitle, " ".join(meta.get("sources", [])), " ".join(meta.get("approvals", []))]
                         + ["%s %s %s" % (g_, c_, d_) for g_, c_, d_, _m, _e in rows] + ["%s %s" % kv for kv in ess] + t["use"] + t["no"])
        SEARCH.append(dict(id=pid, num=num, name=meta["name"], family=meta.get("family", ""), text=re.sub(r"\s+", " ", stext)))
    sid = "f%02d" % gi
    sections.append(f'<section class="cat" id="{sid}"><header class="cat-head"><h2>{E(ftitle)}</h2><p>{E(fdims)}</p></header>{"".join(inner)}</section>')
    toc.append(f'<div class="ix-fam"><h4>{E(ftitle)}</h4>{"".join(tlinks)}</div>')

# documented, not yet built
rest = []
for fam in FAMS:
    for m in fam["members"]:
        if m["presets"]:
            continue
        links = []
        for s_ in m.get("sources", [])[:2]:
            h, ok = linkify(s_)
            links.append(h)
        rest.append("<tr data-s=\"%s\"><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            E(" ".join([fam["title"], m["maker"], m["system"], m["region"], m.get("parts", "")]).lower()),
            E(fam["title"]), E(m["maker"] + " " + m["system"]), E(m["region"]), "<br>".join(links) or E(m["src"])))
n_rest = len(rest)

css = open(CSSF, encoding="utf-8").read()
css += """
.csearch { position: relative; max-width: 560px; }
.csearch svg { position: absolute; left: 12px; top: 19px; width: 17px; height: 17px; transform: translateY(-50%); fill: none; stroke: var(--muted); stroke-width: 2; stroke-linecap: round; pointer-events: none; }
.csearch input { width: 100%; padding: 9px 12px 9px 38px; font: 400 0.98rem var(--f-body); color: var(--ink); background: var(--sheet);
  border: 1.5px solid var(--line); border-radius: 3px; -webkit-appearance: none; appearance: none; }
.csearch input:focus { outline: none; border-color: var(--woodC); }
.csearch .hits { margin-top: 6px; min-height: 1.2em; }
#documented tbody tr[hidden] { display: none; }
.ess { font-size: 0.86rem; } .ess th { width: 34%; font-weight: 600; }
.facts ul { margin: 2px 0 0; padding-left: 1.1rem; display: grid; gap: 3px; }
td.num { white-space: nowrap; font-variant-numeric: tabular-nums; }
.figs .iso-row { grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.25fr); align-items: start; }
.figs .ortho-row { display: grid; grid-template-columns: minmax(0, 3.2fr) minmax(0, 1fr); gap: 10px; overflow: visible; }
.figs .ortho svg { max-width: 100%; height: auto; }
.ess td, .ess td:last-child { width: auto; }
@media (max-width: 760px) { .figs .iso-row { grid-template-columns: minmax(0, 1fr); } }
"""
ICON_PIN = ('<svg class="i-pin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
            '<path d="M9 3h6l-1 6 4 4H6l4-4z"/><path d="M12 13v8"/></svg>'
            '<svg class="i-unpin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
            '<path d="M9 3h6l-1 6 4 4H6l4-4z"/><path d="M12 13v8"/><path d="M3 3l18 18"/></svg>')
ICON_THEME = ('<svg class="i-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
              '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>'
              '<svg class="i-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
              '<rect x="8" y="8" width="8" height="8"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1'
              'M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/></svg>')
BOOT = """<script>(function(){var d=document.documentElement,t=null,p=null;
try{t=localStorage.getItem("scaffvisor-docs-theme");p=localStorage.getItem("scaffvisor-docs-pin");}catch(e){}
d.dataset.theme=(t==="light"||t==="dark")?t:"dark";d.classList.toggle("bar-free",p==="free");})();</script>"""
JS = """(function(){var d=document.documentElement,th=document.getElementById("themeToggle"),pin=document.getElementById("pinToggle");
function save(k,v){try{localStorage.setItem(k,v);}catch(e){}}
function showTheme(){var l=d.dataset.theme==="dark"?th.dataset.light:th.dataset.dark;th.setAttribute("aria-label",l);th.title=l;}
function showPin(){var f=d.classList.contains("bar-free"),l=f?pin.dataset.off:pin.dataset.on;pin.setAttribute("aria-pressed",f?"false":"true");pin.setAttribute("aria-label",l);pin.title=l;}
th.addEventListener("click",function(){d.dataset.theme=d.dataset.theme==="dark"?"light":"dark";save("scaffvisor-docs-theme",d.dataset.theme);showTheme();});
pin.addEventListener("click",function(){d.classList.toggle("bar-free");save("scaffvisor-docs-pin",d.classList.contains("bar-free")?"free":"pinned");showPin();});
showTheme();showPin();
var tt=document.querySelector(".totop");function tog(){tt.classList.toggle("on",window.scrollY>600);}window.addEventListener("scroll",tog,{passive:true});tog();})();"""

SEARCH_JS = r"""(function(){
var q=document.getElementById("cq"),hits=document.getElementById("chits");if(!q)return;
var data=JSON.parse(document.getElementById("cat-index").textContent);
function norm(s){return(s||"").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"");}
data.forEach(function(r){r.n=norm(r.num+" "+r.name+" "+r.family+" "+r.text);});
var rows=Array.prototype.slice.call(document.querySelectorAll("#documented tbody tr"));
rows.forEach(function(tr){tr.n=norm(tr.getAttribute("data-s")+" "+tr.textContent);});
function run(){
  var w=norm(q.value).split(/\s+/).filter(Boolean),shown=0;
  data.forEach(function(r){
    var ok=w.every(function(x){return r.n.indexOf(x)>=0;}),el=document.getElementById(r.id);
    if(el){el.hidden=!ok;}
    var a=document.querySelector('.index a[data-id="'+r.id+'"]');if(a){a.hidden=!ok;}
    if(ok)shown++;
  });
  document.querySelectorAll("section.cat").forEach(function(sec){sec.hidden=!sec.querySelector(".sheet:not([hidden])");});
  document.querySelectorAll(".index .ix-fam").forEach(function(f){if(f.querySelector("a[data-id]")){f.hidden=!f.querySelector("a[data-id]:not([hidden])");}});
  var rshown=0;rows.forEach(function(tr){var ok=w.every(function(x){return tr.n.indexOf(x)>=0;});tr.hidden=!ok;if(ok)rshown++;});
  var ap=document.getElementById("documented");if(ap)ap.hidden=w.length>0&&rshown===0;
  hits.textContent=w.length?(shown+" of "+data.length+" systems"+(rows.length?" · "+rshown+" documented":"")):"";
}
var t;q.addEventListener("input",function(){clearTimeout(t);t=setTimeout(run,80);});
q.addEventListener("keydown",function(e){if(e.key==="Escape"){q.value="";run();}});
document.addEventListener("keydown",function(e){if(e.key==="/"&&document.activeElement!==q&&!/input|textarea/i.test(document.activeElement.tagName)){e.preventDefault();q.focus();q.scrollIntoView({block:"center"});}});
var m=location.search.match(/[?&]q=([^&]+)/);if(m){q.value=decodeURIComponent(m[1].replace(/\+/g," "));run();}
})();"""

CAT_INDEX = json.dumps(SEARCH, ensure_ascii=False).replace("</", "<\\/")
page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scaffold systems catalog</title>
{BOOT}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{css}</style>
</head>
<body>
<header class="topbar" id="topbar" aria-label="Catalog bar">
  <div class="topbar-in">
    <div class="tb-id"><span class="tb-title">ScaffVisor · Scaffold systems</span><span class="tb-ver">Catalog version {VERSION} · {n} systems</span></div>
    <nav class="tb-lang" aria-label="Language"><span aria-current="true">EN</span></nav>
    <button class="tb-btn" id="pinToggle" type="button" aria-pressed="true" data-on="The bar is pinned. Click to unpin it" data-off="The bar scrolls away. Click to pin it">{ICON_PIN}</button>
    <button class="tb-btn" id="themeToggle" type="button" data-dark="Switch to the dark theme" data-light="Switch to the light theme">{ICON_THEME}</button>
  </div>
</header>
<div class="page">
  <header class="masthead">
    <p class="eyebrow">ScaffVisor · Blender add-on</p>
    <h1>Scaffold systems</h1>
    <p class="lede">The {n} systems you can pick in ScaffVisor's <b>System</b> list, grouped by grid: systems in the same group share widths, bay lengths and lift, so their parts fit the same layout; weights and article numbers differ by maker. Each sheet shows a model built by ScaffVisor (2 bays x 2 lifts), dimensioned views, when to use the system, its parts with weights and the documents the numbers come from. {n_rest} more systems are documented at the end, waiting for a published parts list.</p>
    <div class="csearch" role="search">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.8-4.8"/></svg>
      <input id="cq" type="search" placeholder="Search systems, makers, parts, codes" autocomplete="off" spellcheck="false" aria-label="Search the catalog">
      <p id="chits" class="hits" aria-live="polite"></p>
    </div>
    <div class="summary" id="cuprins">
      <div class="legend"><h2 class="h-small">How to read a sheet</h2><ul>
        <li><span>Weights</span><span>guideline values from the manufacturer's list; * = estimated</span></li>
        <li><span>Rules</span><span>ties, braces and wall gap: from the source when it gives them, otherwise placeholders (said on the sheet)</span></li>
        <li><span>Advantages, limits</span><span>common practice and the manufacturers' own descriptions; not a structural assessment</span></li>
        <li><span>Models</span><span>the .blend of every sheet is saved next to the add-on's catalog folder</span></li>
      </ul></div>
      <nav class="index" aria-label="Contents">{"".join(toc)}<div class="ix-fam"><h4>Appendix</h4><a href="#documented"><span class="ix-n">+{n_rest}</span><span>Documented, not yet in ScaffVisor</span></a></div></nav>
    </div>
  </header>
  <main>{"".join(sections)}
  <section class="appendix" id="documented"><h2>Documented, not yet in ScaffVisor</h2>
    <p>Systems found in the collected catalogues and on manufacturers' sites. A preset is added when a parts list with weights is published; the full table with parts counts is on the <a href="../systems.html">systems page</a>.</p>
    <div class="tablewrap"><table><thead><tr><th>Group</th><th>System</th><th>Region</th><th>Source</th></tr></thead><tbody>{"".join(rest)}</tbody></table></div>
  </section></main>
  <footer class="foot"><p>ScaffVisor does not calculate stability and does not replace the manufacturer's instructions or a structural calculation. Weights are catalogue guideline values until weighed on real parts.</p></footer>
</div>
<a class="totop" href="#cuprins" aria-label="Back to contents" title="Back to contents"><span aria-hidden="true">↑</span>TOP</a>
<script type="application/json" id="cat-index">{CAT_INDEX}</script>
<script>{JS}</script>
<script>{SEARCH_JS}</script>
</body>
</html>
'''
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8", newline="\n").write(page)
with open(os.path.join(OUT, "search.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(SEARCH, f, ensure_ascii=False)
print("cards", n, "documented", n_rest, "size", len(page))
