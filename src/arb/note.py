"""Writes the two-page research note, the README's chart and the README's finding from the built study.

    python -m arb.note

JKM-TTF-Arbitrage-Research-Note.pdf   two A4 pages, set in Liberation Serif
assets/reroute-levels.png             the landing chart, for the README
README.md                             the block between the two finding markers
"""

from __future__ import annotations

import io
import json
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.textpath import TextToPath  # noqa: E402

from . import engine, params  # noqa: E402

ROOT = params.ROOT
FONTS = ROOT / "vendor" / "liberation-serif"
REGULAR = font_manager.FontProperties(fname=str(FONTS / "LiberationSerif-Regular.ttf"))
BOLD = font_manager.FontProperties(fname=str(FONTS / "LiberationSerif-Bold.ttf"))
ITALIC = font_manager.FontProperties(fname=str(FONTS / "LiberationSerif-Italic.ttf"))
for face in ("Regular", "Bold", "Italic"):
    font_manager.fontManager.addfont(str(FONTS / ("LiberationSerif-%s.ttf" % face)))
plt.rcParams.update({"font.family": "Liberation Serif", "pdf.fonttype": 42, "axes.unicode_minus": False, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8b8d93", "axes.labelcolor": "#55575e", "xtick.color": "#55575e", "ytick.color": "#55575e",
                     "axes.grid": True, "grid.color": "#e6e3dc", "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "axes.labelsize": 9})

INK, MUTED, ACCENT = "#17181c", "#55575e", "#8e2b2b"
COLOUR = {"panama": "#2a78d6", "cape": "#eb6834", "suez": "#1baf7a", "europe": "#6b6e75"}
NAME = {"panama": "via Panama", "cape": "via the Cape", "suez": "via Suez"}
W, H = 8.27, 11.69            # A4, inches
LEFT, RIGHT = 0.80, 0.80      # margins, inches
MONTHS = "January February March April May June July August September October November December".split()


def n(x: float, digits: int = 2) -> str:
    return format(x, ",.%df" % digits)


def day(iso: str) -> str:
    y, m, d = (int(v) for v in iso[:10].split("-"))
    return "%d %s %d" % (d, MONTHS[m - 1], y)


def month(iso: str) -> str:
    return "%s %s" % (MONTHS[int(iso[5:7]) - 1], iso[:4])


class Page:
    """Text set from the top of an A4 page, in inches, with word wrap measured in the real font."""

    def __init__(self, pdf):
        self.fig = plt.figure(figsize=(W, H))
        self.pdf = pdf
        self.y = 0.75

    def width(self, text: str, font, size: float) -> float:
        prop = font.copy()
        prop.set_size(size)
        return TextToPath().get_text_width_height_descent(text, prop, ismath=False)[0] / 72.0

    def text(self, text: str, font=REGULAR, size: float = 10.5, colour: str = INK, leading: float = 1.32,
             x: float = LEFT, width: float | None = None, after: float = 0.10) -> None:
        width = width or (W - LEFT - RIGHT)
        line, lines = "", []
        for word in text.split():
            trial = (line + " " + word).strip()
            if self.width(trial, font, size) <= width:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
        for ln in lines:
            self.fig.text(x / W, 1 - self.y / H, ln, fontproperties=font, fontsize=size, color=colour, va="top", ha="left")
            self.y += size * leading / 72.0
        self.y += after

    def axes(self, height: float, left: float = LEFT + 0.35, right: float = RIGHT + 0.05, after: float = 0.38):
        ax = self.fig.add_axes([left / W, 1 - (self.y + height) / H, (W - left - right) / W, height / H])
        self.y += height + after
        return ax

    def row(self, cells: list[str], stops: list[float], font=REGULAR, size: float = 9.3, colour: str = INK, after: float = 0.0) -> None:
        """One table row: the first cell starts at the left margin, the others end at their stops (inches from the left margin)."""
        for i, (cell, stop) in enumerate(zip(cells, stops)):
            self.fig.text((LEFT + stop) / W, 1 - self.y / H, cell, fontproperties=font, fontsize=size, color=colour,
                          va="top", ha="left" if i == 0 else "right")
        self.y += size * 1.45 / 72.0 + after

    def rule(self) -> None:
        self.fig.add_artist(plt.Line2D([LEFT / W, 1 - RIGHT / W], [1 - self.y / H] * 2, color="#d8d5cd", linewidth=0.7))
        self.y += 0.12

    def close(self, footer: str) -> float:
        """Saves the page and returns by how many inches its content runs past the bottom margin (negative: room left)."""
        self.fig.text(LEFT / W, 0.36 / H, footer, fontproperties=REGULAR, fontsize=8, color=MUTED, va="bottom")
        self.pdf.savefig(self.fig)
        plt.close(self.fig)
        return self.y - (H - 0.62)


# ---------------------------------------------------------------------------
# The three charts
# ---------------------------------------------------------------------------

def chart_reroute(ax, study: dict) -> None:
    inputs = study["now"]["preset"]["inputs"]
    result = study["now"]["result"]
    top = max(200_000, int(-(-inputs["hire"] * 1.15 // 50_000)) * 50_000)       # the axis always reaches today's charter rate
    for rid in ("panama", "suez", "cape"):
        a, b = engine.breakeven_line(inputs, rid)
        is_open = result["routes"][rid]["open"]
        ax.plot([0, top], [a, a + b * top], color=COLOUR[rid], linewidth=1.8, linestyle="-" if is_open else (0, (1, 2.5)))
        ax.annotate(NAME[rid] + ("" if is_open else " (closed)"), (top, a + b * top), xytext=(5, 6 if rid == "cape" else (-9 if rid == "suez" else 0)),
                    textcoords="offset points", fontsize=9, color=INK, va="center", annotation_clip=False)
    spread, hire = result["spread"], inputs["hire"]
    ax.axhline(spread, color=ACCENT, linewidth=1.2)
    ax.axvline(hire, color=ACCENT, linewidth=0.8, linestyle=(0, (3, 3)))
    ax.plot([hire], [spread], "o", color=ACCENT, markersize=6, markeredgecolor="white", markeredgewidth=1.2, zorder=5)
    ax.annotate("JKM minus TTF this week, %s" % n(spread), (top, spread), xytext=(-4, 5), textcoords="offset points",
                ha="right", fontsize=9, color=ACCENT)
    ax.annotate("%s a day" % n(hire, 0), (hire, ax.get_ylim()[1]), xytext=(5, -2), textcoords="offset points", fontsize=9, color=ACCENT, va="top")
    ax.axhline(0, color="#8b8d93", linewidth=0.7)
    ax.set_xlim(0, top)
    ticks = [top * i // 4 for i in range(5)]
    ax.set_xticks(ticks, [n(t, 0) for t in ticks])
    ax.set_xlabel("Charter rate, USD a day")
    ax.set_ylabel("Reroute level, JKM minus TTF, USD/MMBtu")


def chart_history(ax, study: dict) -> None:
    rows = study["history"]["weekly"]
    dates = [date.fromisoformat(r["date"]) for r in rows]
    # runs of weeks with no hole longer than three weeks: nothing is drawn across missing prices
    runs, start = [], 0
    for i in range(1, len(rows) + 1):
        if i == len(rows) or (dates[i] - dates[i - 1]).days > 21:
            runs.append((start, i))
            start = i
    for a, b in runs:
        shade = None
        for i in range(a, b + 1):
            is_open = i < b and rows[i]["open"]
            if is_open and shade is None:
                shade = i
            if not is_open and shade is not None:
                ax.axvspan(dates[shade], dates[i - 1], color="#17181c", alpha=0.07, linewidth=0)
                shade = None
        first = a
        for i in range(a + 1, b + 1):
            if i == b or rows[i]["route"] != rows[first]["route"]:
                seg = slice(first, min(i + 1, b))
                ax.plot(dates[seg], [r["breakeven"] for r in rows[seg]], color=COLOUR[rows[first]["route"]], linewidth=1.2)
                first = i
        ax.plot(dates[a:b], [r["spread"] for r in rows[a:b]], color=INK, linewidth=1.0)
    ax.plot([dates[-1]], [max(-6, min(8, rows[-1]["spread"]))], "o", color=ACCENT, markersize=5, markeredgecolor="white", markeredgewidth=1, zorder=5, clip_on=False)
    ax.axhline(0, color="#8b8d93", linewidth=0.7)
    ax.set_ylim(-6, 8)
    ax.set_xlim(dates[0], dates[-1])
    ax.set_ylabel("USD/MMBtu")
    low, high = min(rows, key=lambda r: r["spread"]), max(rows, key=lambda r: r["spread"])
    if low["spread"] < -6:
        ax.annotate("off the scale: %s in %s" % (n(low["spread"], 1), month(low["date"])), (date.fromisoformat(low["date"]), -6),
                    xytext=(6, 5), textcoords="offset points", fontsize=8.5, color=MUTED)
    if high["spread"] > 8:
        ax.annotate("off the scale: %s in %s" % (n(high["spread"], 1), month(high["date"])), (date.fromisoformat(high["date"]), 8),
                    xytext=(6, -11), textcoords="offset points", fontsize=8.5, color=MUTED)
    labelled = [e for e in study["events"] if "weekly" in e.get("on", []) and e["date"] >= rows[0]["date"]]
    for i, e in enumerate(sorted(labelled, key=lambda e: e["date"])):
        d = date.fromisoformat(e["date"])
        ax.axvline(d, color="#8b8d93", linewidth=0.6, linestyle=(0, (1, 3)))
        ax.annotate(e["label"], (d, 8), xytext=(2, 4 + 9 * (i % 2)), textcoords="offset points", fontsize=7.5, color=MUTED,
                    annotation_clip=False)


def chart_flows(ax, study: dict) -> None:
    months = [m for m in study["flows"]["months"] if m["month"] >= "2016-02"]
    by_month = {m["month"]: m for m in months}
    dates = [date.fromisoformat(m["month"] + "-15") for m in months]
    for i, m in enumerate(months):
        y, mo = int(m["month"][:4]), int(m["month"][5:7])
        prior = by_month.get("%04d-%02d" % ((y, mo - 1) if mo > 1 else (y - 1, 12)))
        if prior and prior["open"]:
            ax.axvspan(date(y, mo, 1), date(y + (mo == 12), mo % 12 + 1, 1), color="#17181c", alpha=0.07, linewidth=0)
    ax.plot(dates, [m["share_jkm"] * 100 for m in months], color=INK, linewidth=1.2)
    ax.plot([dates[-1]], [months[-1]["share_jkm"] * 100], "o", color=ACCENT, markersize=5, markeredgecolor="white", markeredgewidth=1, zorder=5)
    ax.set_ylim(0, 72)
    ax.set_xlim(dates[0], dates[-1])
    ax.set_ylabel("Percent")


# ---------------------------------------------------------------------------
# The note
# ---------------------------------------------------------------------------

def facts(study: dict) -> dict:
    now, result = study["now"], study["now"]["result"]
    inputs = now["preset"]["inputs"]
    table = {row["route"]: row for row in now["table"]}
    weekly = study["history"]["weekly"]
    by_year: dict[str, list[int]] = {}
    for r in weekly:
        by_year.setdefault(r["date"][:4], [0, 0])
        by_year[r["date"][:4]][0] += r["open"]
        by_year[r["date"][:4]][1] += 1
    full = {y: v for y, v in by_year.items() if v[1] >= 20}
    best = max(full, key=lambda y: full[y][0] / full[y][1])
    worst = min(full, key=lambda y: full[y][0] / full[y][1])
    lift, run = [], []
    for row in study["flows"]["lift"] + [{"margin_europe": None}]:      # the longest run of months that did not cover the gas
        if row["margin_europe"] is not None and row["margin_europe"] < 0:
            run.append(row)
        else:
            lift, run = (run if len(run) > len(lift) else lift), []
    return {"now": now, "result": result, "inputs": inputs, "table": table, "weekly": weekly,
            "summary": study["history"]["summary"]["weekly"], "best": (best, full[best]), "worst": (worst, full[worst]),
            "flows": study["flows"], "lift": lift,
            "cancelled": sum(r["cancelled"] for r in study["flows"]["lift"]), "canal": now["canal"]}


def closes_above(hire: float) -> str:
    """The charter rate at which a route stops paying, short enough for a table cell."""
    if hire <= 0:
        return "shut at any rate"
    return "%s million USD a day" % n(hire / 1e6) if hire >= 1e6 else "%s USD a day" % n(hire, 0)


def listed(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def headline(study: dict) -> dict:
    """The landing sentence in parts, by the site's own rules: only open routes count, and the charter rate says where it comes from."""
    now = study["now"]
    r, inputs, src = now["result"], now["preset"]["inputs"], now["preset"]["sources"]
    spread = r["spread"]
    open_routes = [rid for rid in ("panama", "suez", "cape") if r["routes"][rid]["open"]]
    clears = [rid for rid in open_routes if spread > r["routes"][rid]["breakeven_spread"]]
    count = {1: "", 2: " on both routes", 3: " on all three routes"}[len(open_routes)]
    if len(clears) == len(open_routes):
        verdict = "the arb is open" + count
    elif not clears:
        verdict = "the arb is closed" + count
    else:
        verdict = "the arb is open %s only" % listed([NAME[rid] for rid in clears])
    hire = src["hire"]
    if hire["status"] == "assumed":
        rate = "the low scenario, no rate having been reported since %s" % day(str(hire["last_reported"]))
        caveat = "No charter rate has been reported since %s, so the low scenario stands in; a real fixture differs." % day(str(hire["last_reported"]))
    else:
        rate = "the %scharter rate reported, on %s" % ("" if hire["status"] == "reported" else "last ", day(str(hire["date"])))
        caveat = "The charter rate is one published assessment (Spark30S Atlantic), reported on %s%s; a real fixture differs." % (
            day(str(hire["date"])), "" if hire["status"] == "reported" else " and held since")
    des = inputs["des_discount"]
    bare = now["without_discount"]
    europe = ("A cargo delivered to Northwest Europe sells %s under TTF; without that discount the level%s would be %s."
              % (n(-des), "" if len(open_routes) == 1 else "s", listed([n(bare[rid]) for rid in open_routes]))
              if des < 0 else "A cargo delivered to Northwest Europe sells %s over TTF." % n(des))
    return {
        "spread": "JKM is %s USD/MMBtu %s TTF." % (n(abs(spread)), "above" if spread >= 0 else "below"),
        "rate": rate, "hire": n(inputs["hire"], 0), "caveat": caveat, "verdict": verdict, "europe": europe,
        "levels": listed(["%s %s" % (n(r["routes"][rid]["breakeven_spread"]), NAME[rid]) for rid in open_routes]),
        "shut": [rid for rid in ("panama", "suez", "cape") if rid not in open_routes],
    }


def flows_sentence(flows: dict) -> str:
    t, before, since = flows["test"], flows["before_2022"], flows["since_2022"]
    pc = lambda side: n(side["mean_share"] * 100, 0)   # noqa: E731
    return ("After a month with the arb open, %s percent of US LNG left for Japan, South Korea, China and Taiwan; after a closed month, %s percent. "
            "The gap belongs to the years before 2022, when the arb was open in %d months of %d and the share was %s percent; since 2022 it is %s percent "
            "after an open month and %s after a closed one."
            % (pc(t["open"]), pc(t["closed"]), before["open"]["months"], before["months"], pc(before["open"]), pc(since["open"]), pc(since["closed"])))


CHARTS = (2.40 + 2.35, 2.05)     # inches of chart on each page at full height


def compose(target, study: dict, scale: tuple[float, float] = (1.0, 1.0)) -> list[float]:
    """Sets the two pages with each page's charts at a share of their full height; returns each page's overflow in inches."""
    f = facts(study)
    hl = headline(study)
    r, inputs, table = f["result"], f["inputs"], f["table"]
    pan, cape, eur = r["routes"]["panama"], r["routes"]["cape"], r["routes"]["europe"]
    src = study["now"]["preset"]["sources"]
    footer = "Nathan Couturier. JKM-TTF arbitrage study: https://nathancouturier.github.io/jkm-ttf-arbitrage/   Data to %s." % day(study["data_date"])
    over = []
    with PdfPages(target, metadata={"Title": "JKM-TTF arbitrage: research note", "Author": "Nathan Couturier",
                                    "Subject": "US Gulf LNG netbacks to Europe and Asia", "Creator": "arb.note", "Producer": "matplotlib",
                                    "CreationDate": None, "ModDate": None}) as pdf:
        p = Page(pdf)
        p.text("JKM-TTF ARBITRAGE STUDY  ·  RESEARCH NOTE  ·  WEEK TO %s" % day(study["data_date"]).upper(), size=8.5, colour=MUTED, after=0.12)
        p.text("When a US Gulf LNG cargo pays to go east", font=BOLD, size=21, leading=1.15, after=0.14)
        p.text("%s At %s USD a day, %s, a cargo loaded at Sabine Pass pays to go to Japan instead of Rotterdam above a spread of %s, so %s."
               % (hl["spread"], hl["hire"], hl["rate"], hl["levels"], hl["verdict"]), font=BOLD, size=12.5, leading=1.3, after=0.10)
        open_routes = [rid for rid in ("panama", "suez", "cape") if r["routes"][rid]["open"]]
        p.text("%s (ACER, to %s). Each 10,000 USD a day on the charter rate adds %s to the Panama level and %s to the Cape level, because the Cape "
               "adds %s days to the round trip and Panama %s. With the ship already paid for the level%s %s."
               % (hl["europe"][:-1], day(str(src["des_discount"]["date"])) if src["des_discount"]["date"] else "an assumption",
                  n(pan["spread_slope_per_usd_day"] * 1e4), n(cape["spread_slope_per_usd_day"] * 1e4),
                  n(cape["round_trip_days"] - eur["round_trip_days"], 0), n(pan["round_trip_days"] - eur["round_trip_days"], 0),
                  " is" if len(open_routes) == 1 else "s are", listed([n(table[rid]["sunk"]) for rid in open_routes])), after=0.16)
        p.text("Chart 1. The longer the route, the faster its reroute level rises with the charter rate", font=BOLD, size=10, after=0.04)
        chart_reroute(p.axes(2.40 * scale[0], right=RIGHT + 1.05, after=0.52), study)
        sc = study["now"]["preset"]["scenarios"]
        stops = [0.0, 2.95, 3.80, 4.75, 5.55, 6.67]
        p.row(["Reroute level by charter rate, USD/MMBtu", "ship paid for, 0", "low, %s" % n(sc["low"], 0), "central, %s" % n(sc["central"], 0),
               "high, %s" % n(sc["high"], 0), "arb closes above"], stops, font=ITALIC, size=8.8, colour=MUTED, after=0.02)
        for rid in ("panama", "suez", "cape"):
            row = table[rid]
            p.row([NAME[rid] + ("" if row["open"] else " (closed)"), n(row["sunk"]), n(row["low"]), n(row["central"]), n(row["high"]),
                   closes_above(row["breakeven_hire"])], stops)
        p.y += 0.16
        s = f["summary"]
        p.text("Chart 2. The spread cleared the level in %d of %d weeks, most often in %s and least in %s"
               % (s["arb_open"], s["observations"], f["best"][0], f["worst"][0]), font=BOLD, size=10, after=0.03)
        p.text("JKM minus TTF (black) and the reroute level of the cheapest open route at the reported charter rate (coloured by route). "
               "Shaded: the arb is open. With the ship already paid for it was open in %d weeks." % s["arb_open_sunk"], size=8.8, colour=MUTED, after=0.05)
        p.y += 0.30
        chart_history(p.axes(2.35 * scale[0], after=0.3), study)
        over.append(p.close(footer + "   Page 1 of 2"))

        p = Page(pdf)
        p.text("Did cargoes follow?", font=BOLD, size=13, after=0.06)
        p.text(flows_sentence(f["flows"]) + " Europe's pull, term contracts and China's tariff on US LNG have kept Asia's share low whatever the arb "
               "(%d months of the Department of Energy's cargo record; the rule was fixed before the result was computed)." % f["flows"]["test"]["months"], after=0.12)
        p.text("Chart 3. Share of US LNG sent to JKM markets. Shaded: the arb was open the month before", font=BOLD, size=10, after=0.04)
        chart_flows(p.axes(2.05 * scale[1], after=0.34), study)
        lift = f["lift"]
        p.text("The same cargo answers two more questions", font=BOLD, size=13, after=0.06)
        if lift:
            p.text("When does the arb close on the cargo itself? A buyer lifts a cargo when its best netback covers 115 percent of Henry Hub. "
                   "From %s to %s a cargo sold in Europe did not, and about %d US cargoes were cancelled."
                   % (month(lift[0]["month"]).split()[0], month(lift[-1]["month"]), f["cancelled"]), after=0.06)
        p.text("What is a Panama slot worth? %sThrough Panama the round trip is %s days shorter than round the Cape. At this week's charter rate and gas "
               "price a ship %s pay %s million USD above the tariff for its two transits, or wait %s days at each, before the Cape is the cheaper way east."
               % ("" if pan["open"] else "The canal is not open to this cargo this week; were it, the sum would run as follows. ",
                  n(cape["round_trip_days"] - pan["round_trip_days"], 0), "can" if pan["open"] else "could", n(f["canal"]["premium_usd"] / 1e6), n(f["canal"]["wait_days"], 1)), after=0.14)

        p.text("Method", font=BOLD, size=13, after=0.06)
        box_top = p.y
        mono = font_manager.FontProperties(family="DejaVu Sans Mono")
        ship = inputs["ship"]
        for ln in ["loaded     = capacity x fill x MMBtu per m3          %s m3 x %s percent x %s = %s MMBtu"
                   % (n(ship["capacity_m3"], 0), n(ship["fill"] * 100, 1), n(ship["mmbtu_per_m3"], 0), n(eur["loaded"], 0)),
                   "delivered  = loaded - %s percent a day x round trip days       the boil-off is the ship's fuel" % n(ship["boil_off"] * 100, 3),
                   "cost       = hire x round trip days + ports + canal tolls and fees + EU ETS (Europe) + financing",
                   "netback    = (DES price x delivered - cost) / loaded      Europe: TTF less the DES discount. Asia: JKM",
                   "S*(route)  = the JKM minus TTF spread at which netback(Asia, route) = netback(Europe)",
                   "H*(route)  = the charter rate at which the two netbacks are equal at today's prices",
                   "lift       = best netback - 115 percent of Henry Hub      the fixed liquefaction fee is sunk"]:
            p.fig.text((LEFT + 0.12) / W, 1 - (p.y + 0.10) / H, ln, fontproperties=mono, fontsize=7.6, color=INK, va="top")
            p.y += 0.175
        p.y += 0.16
        p.fig.add_artist(plt.Rectangle((LEFT / W, 1 - p.y / H), (W - LEFT - RIGHT) / W, (p.y - box_top) / H, fill=False, edgecolor="#b9b6ae", linewidth=0.7))
        p.y += 0.12
        p.text("Both prices are delivered ex-ship: Europe's is TTF less the discount ACER assesses, the market's charge for regasification and entry. "
               "Hire runs for the round trip, as in the Spark30S freight assessment, whose worked example the model reproduces to the dollar. "
               "This week: Gate %s days and a netback of %s; Panama %s days and %s; the Cape %s days and %s, in USD per MMBtu loaded."
               % (n(eur["round_trip_days"], 1), n(eur["netback"]), n(pan["round_trip_days"], 1), n(pan["netback"]),
                  n(cape["round_trip_days"], 1), n(cape["netback"])), size=9.6, after=0.14)

        p.text("Caveats", font=BOLD, size=13, after=0.06)
        for line in [
            hl["caveat"],
            "Europe's DES discount is ACER's assessment against TTF over the same five days, averaged over 20; until January 2023 it is an assumption.",
            "Panama is priced at the tariff with a booked slot. Slots are auctioned and their price is not published.",
            "Prices are weekly averages of front months, which can name different delivery months; a cargo is sold further out.",
            "Flows show association, not cause. Nothing here is a forecast or a trading signal.",
        ]:
            p.text("•  " + line, size=9.4, after=0.01)
        p.y += 0.06
        p.rule()
        p.text("Sources: U.S. Energy Information Administration (JKM and TTF, credited to Bloomberg Finance L.P.; Henry Hub), ACER, U.S. Department of "
               "Energy, Spark Commodities as reported by LNG Prime, Panama Canal Authority, Suez Canal Authority, Federal Reserve Board, Federal Reserve "
               "Bank of New York, European Commission and DEHSt, METI, World Bank. Every figure and its source: the site's Method view.",
               size=8.0, colour=MUTED, leading=1.25)
        over.append(p.close(footer + "   Page 2 of 2"))
    return over


def write_note(study: dict, path=None) -> tuple[float, float]:
    """Writes the note with each page's charts as tall as its text allows, so a longer sentence never stops the build."""
    path = path or ROOT / "JKM-TTF-Arbitrage-Research-Note.pdf"
    scale = [1.0, 1.0]
    for _ in range(4):
        buffer = io.BytesIO()
        over = compose(buffer, study, tuple(scale))
        if max(over) <= 0:
            break
        # the charts give up exactly what the text needs, and a little more
        scale = [max(0.45, s - (o + 0.03) / full) if o > 0 else s for s, o, full in zip(scale, over, CHARTS)]
    path.write_bytes(buffer.getvalue())
    return tuple(scale)


def write_readme_chart(study: dict) -> None:
    fig = plt.figure(figsize=(9.2, 3.5), facecolor="#fbfaf8")
    ax = fig.add_axes([0.075, 0.165, 0.76, 0.70], facecolor="#fbfaf8")
    chart_reroute(ax, study)
    fig.text(0.075, 0.955, "Reroute levels by route, week to %s" % day(study["data_date"]), fontproperties=BOLD, fontsize=12, color=INK, va="top")
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    fig.savefig(out / "reroute-levels.png", dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def readme_finding(study: dict) -> str:
    """The README's finding in two paragraphs: the landing sentence with its levels, then the history and the flows."""
    f = facts(study)
    hl = headline(study)
    r, table, s = f["result"], f["table"], f["summary"]
    open_routes = [rid for rid in ("panama", "suez", "cape") if r["routes"][rid]["open"]]
    paid = "With the ship already paid for the level%s %s." % (
        " is" if len(open_routes) == 1 else "s are", listed([n(table[rid]["sunk"]) for rid in open_routes]))
    clears = [rid for rid in open_routes if r["spread"] > r["routes"][rid]["breakeven_spread"]]
    closes = " ".join("The arb %s closes above a charter rate of %s." % (NAME[rid], closes_above(r["routes"][rid]["breakeven_hire"])) for rid in clears[:1])
    return "\n".join([
        "**Week to %s.** %s At %s USD a day, %s, a cargo pays to go east above %s, so %s. %s %s %s"
        % (day(study["data_date"]), hl["spread"], hl["hire"], hl["rate"], hl["levels"], hl["verdict"], hl["europe"], paid, closes),
        "",
        "Since %s the spread has cleared the level of the cheapest open route in %d of %d weeks at the reported charter rate, and in %d with the ship already paid for. %s"
        % (month(s["first"]), s["arb_open"], s["observations"], s["arb_open_sunk"], flows_sentence(f["flows"])),
    ]).replace(" \n", "\n").rstrip()


def write_readme_finding(study: dict) -> None:
    """Keeps the README's finding in step with the data: rewrites the block between its two markers."""
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    start, end = "<!-- finding:start -->", "<!-- finding:end -->"
    head, rest = text.split(start)
    path.write_text(head + start + "\n" + readme_finding(study) + "\n" + end + rest.split(end)[1], encoding="utf-8")


if __name__ == "__main__":
    built = json.loads((ROOT / "site" / "data" / "study.json").read_text())
    used = write_note(built)
    write_readme_chart(built)
    write_readme_finding(built)
    print("wrote JKM-TTF-Arbitrage-Research-Note.pdf (charts at %d and %d percent of full height), assets/reroute-levels.png and the README's finding"
          % (round(used[0] * 100), round(used[1] * 100)))
