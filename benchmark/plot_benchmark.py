"""Figures of the review (run with no arguments for the benchmark figures, Figs. 6-8), with an automatic layout check.

Every figure is passed through qa(): after drawing, each text's rendered bounding box must
(i) lie inside the box it belongs to (with padding), (ii) not overlap any other text, and
(iii) not be crossed by any connector line or arrow. qa() raises on any violation, so a
figure is only saved if it passes.
Output names follow the final figure numbers of the manuscript.
"""
import sys, os, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch
from matplotlib.lines import Line2D
from matplotlib.transforms import Bbox

OUT = sys.argv[1] if len(sys.argv) > 1 else "figures"
os.makedirs(OUT, exist_ok=True)
BENCH = "."
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#555", "axes.linewidth": 0.8,
                     "mathtext.fontset": "dejavusans"})
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, MUTED, LIGHTBLUE, GREY, CREAM, PALE = "#1f1f1f", "#5a5a5a", "#e8f0fb", "#ececec", "#fff6e8", "#fafafa"
BROWN = "#9c4a06"


class Canvas:
    """Axes in [0,1]^2 that remembers boxes, texts and connectors for the layout check."""
    def __init__(self, w, h):
        self.fig = plt.figure(figsize=(w, h))
        self.ax = self.fig.add_axes([0, 0, 1, 1]); self.ax.set_xlim(0, 1); self.ax.set_ylim(0, 1); self.ax.axis("off")
        self.owned = []      # (text, patch) text must stay inside patch
        self.free = []       # texts without an owner
        self.conn = []       # connector artists
        self.boxes = []

    def box(self, x, y, w, h, title=None, body=None, fc="white", ec=INK, tsize=8.2, bsize=7.3, bold=True, lw=1.0, align="center"):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.01", fc=fc, ec=ec, lw=lw, zorder=2)
        self.ax.add_patch(p); self.boxes.append(p)
        hx = x + w / 2 if align == "center" else x + 0.012
        if title and body:
            H = self.fig.get_figheight() * 72.0                      # figure height in points
            th = (title.count("\n") + 1) * tsize * 1.25 / H
            bh = (body.count("\n") + 1) * bsize * 1.3 / H
            gap = 0.45 * bsize / H
            top = y + h / 2 + (th + gap + bh) / 2
            t1 = self.ax.text(hx, top, title, ha=align, va="top", fontsize=tsize, fontweight="bold" if bold else "normal", linespacing=1.15, zorder=3)
            t2 = self.ax.text(hx, top - th - gap, body, ha=align, va="top", fontsize=bsize, linespacing=1.3, zorder=3)
            self.owned += [(t1, p), (t2, p)]
        else:
            t = self.ax.text(x + w / 2, y + h / 2, title or body, ha="center", va="center", fontsize=tsize if title else bsize,
                             fontweight="bold" if (title and bold) else "normal", linespacing=1.3, zorder=3)
            self.owned.append((t, p))
        return (x, y, w, h)

    def text(self, x, y, s, **kw):
        kw.setdefault("zorder", 3)
        t = self.ax.text(x, y, s, **kw); self.free.append(t); return t

    def line(self, xs, ys, **kw):
        kw.setdefault("color", INK); kw.setdefault("lw", 1.0); kw.setdefault("zorder", 1)
        l, = self.ax.plot(xs, ys, **kw); self.conn.append(l); return l

    def arrow(self, p1, p2, color=INK, lw=1.0, rad=0.0, style="-|>", ls="-"):
        a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=10, lw=lw, color=color, linestyle=ls,
                            connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0, zorder=1)
        self.ax.add_patch(a); self.conn.append(a); return a


def _segments(artist, renderer):
    if isinstance(artist, Line2D):
        xy = artist.get_transform().transform(np.c_[artist.get_xdata(), artist.get_ydata()])
    else:  # FancyArrowPatch: path is in display coordinates after drawing
        xy = artist.get_path().vertices
    pts = []
    for a, b in zip(xy[:-1], xy[1:]):
        for s in np.linspace(0, 1, 30):
            pts.append(a + s * (b - a))
    return np.array(pts)


def qa(fig, owned=(), free=(), conn=(), circles=(), name="", pad=2.0):
    """Raise if any text leaves its box, overlaps another text, or is crossed by a connector."""
    fig.canvas.draw(); r = fig.canvas.get_renderer(); problems = []
    texts = [t for t, _ in owned] + list(free)
    bb = {id(t): t.get_window_extent(r) for t in texts if t.get_text().strip()}
    for t, p in owned:
        if id(t) not in bb: continue
        pb = p.get_window_extent(r); tb = bb[id(t)]
        if tb.x0 < pb.x0 + pad or tb.x1 > pb.x1 - pad or tb.y0 < pb.y0 + pad or tb.y1 > pb.y1 - pad:
            problems.append(f"text outside box: {t.get_text()[:40]!r}")
    keys = list(bb)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = bb[keys[i]], bb[keys[j]]
            if a.x0 < b.x1 - 1 and b.x0 < a.x1 - 1 and a.y0 < b.y1 - 1 and b.y0 < a.y1 - 1:
                ti = next(t for t in texts if id(t) == keys[i]); tj = next(t for t in texts if id(t) == keys[j])
                problems.append(f"text overlap: {ti.get_text()[:30]!r} / {tj.get_text()[:30]!r}")
    for c in conn:
        pts = _segments(c, r)
        for k, b in bb.items():
            inside = (pts[:, 0] > b.x0 + 1) & (pts[:, 0] < b.x1 - 1) & (pts[:, 1] > b.y0 + 1) & (pts[:, 1] < b.y1 - 1)
            if inside.any():
                t = next(t for t in texts if id(t) == k)
                problems.append(f"line crosses text: {t.get_text()[:40]!r}")
        for (cx, cy, rad, tr, lab) in circles:   # connectors must not pass through a node they do not end at
            c0 = tr.transform((cx, cy)); rr = abs(tr.transform((cx + rad, cy))[0] - c0[0])
            d = np.hypot(pts[:, 0] - c0[0], pts[:, 1] - c0[1])
            ends = np.r_[np.hypot(*(pts[0] - c0)), np.hypot(*(pts[-1] - c0))]
            if (ends > rr * 1.05).all() and (d < rr * 0.95).any():
                problems.append(f"line passes through node {lab}")
    if problems:
        raise RuntimeError(f"{name}: " + "; ".join(sorted(set(problems))))
    print(f"{name}: layout check passed ({len(bb)} texts, {len(list(conn))} connectors)")


def save(c, name, **kw):
    qa(c.fig, c.owned, c.free, c.conn, name=name, **kw)
    c.fig.savefig(f"{OUT}/{name}.png", dpi=300); plt.close(c.fig)


# ============================================================ Fig. 1 record flow (PRISMA 2020 format)
def fig1():
    c = Canvas(7.4, 7.6)
    A, B, C, D = (0.07, 0.205), (0.295, 0.205), (0.52, 0.205), (0.745, 0.235)   # column x, width
    for y0, y1, lab in [(0.785, 0.985, "Identification"), (0.34, 0.765, "Screening"), (0.165, 0.32, "Included"), (0.005, 0.145, "Probes")]:
        c.text(0.025, (y0 + y1) / 2, lab, rotation=90, ha="center", va="center", fontsize=8, fontweight="bold", color=MUTED)
    dbs = [("Scopus", "TITLE-ABS-KEY\nn = 316"), ("IEEE Xplore", "3 sub-queries\nn = 465"), ("Web of Science", "TS field\nn = 170"), ("ScienceDirect", "coverage check\nn = 5")]
    xs = [0.07, 0.30, 0.53, 0.76]
    for (t, b), x in zip(dbs, xs):
        c.box(x, 0.895, 0.21, 0.09, t, b, fc=LIGHTBLUE)
        c.line([x + 0.105] * 2, [0.895, 0.875])
    c.line([xs[0] + 0.105, xs[-1] + 0.105], [0.875, 0.875])
    c.arrow((0.5225, 0.875), (0.5225, 0.86))
    c.box(0.295, 0.785, 0.455, 0.075, "Merged and de-duplicated", "DOI, then database ID, then title + year\n956 retrieved − 285 duplicates = 671 unique records")
    c.arrow((B[0] + B[1] / 2, 0.785), (B[0] + B[1] / 2, 0.765)); c.arrow((C[0] + C[1] / 2, 0.785), (C[0] + C[1] / 2, 0.765))
    c.box(B[0], 0.34, B[1], 0.425, "Scopus records", "n = 316\n\nscreened by the\nauthor on title,\nabstract and\nkeywords\n\ndecisions verified\nby a second reader")
    c.box(C[0], 0.665, C[1], 0.10, "Records new to\nthe corpus", "n = 355 (IEEE Xplore,\nWeb of Science)")
    c.box(D[0], 0.68, D[1], 0.07, None, "Excluded: query terms only\noutside title, abstract and\nkeywords   n = 282", fc=GREY)
    c.arrow((C[0] + C[1], 0.715), (D[0], 0.715))
    c.arrow((C[0] + C[1] / 2, 0.665), (C[0] + C[1] / 2, 0.635))
    c.box(C[0], 0.34, C[1], 0.295, "Screened on title\nand abstract", "n = 73\n\ncriteria applied with\nlanguage-model\nassistance\n\ndecisions verified\nby a second reader")
    c.box(D[0], 0.47, D[1], 0.13, "Excluded  n = 18", "FL not substantive 13\nfocal term incidental or\nin another sense 4\neditorial 1", fc=GREY)
    c.arrow((C[0] + C[1], 0.535), (D[0], 0.535))
    c.box(D[0], 0.36, D[1], 0.07, "Unresolved  n = 2", "full text required", fc="white")
    c.arrow((C[0] + C[1], 0.395), (D[0], 0.395))
    c.box(A[0], 0.47, A[1], 0.17, "Excluded  n = 123", "front matter 22\nFL not substantive 78\nfocal term incidental\nor in another sense 23", fc=GREY)
    c.arrow((B[0], 0.555), (A[0] + A[1], 0.555))
    c.box(A[0], 0.36, A[1], 0.07, "Unresolved  n = 2", "full text required", fc="white")
    c.arrow((B[0], 0.395), (A[0] + A[1], 0.395))
    c.arrow((B[0] + B[1] / 2, 0.34), (B[0] + B[1] / 2, 0.32)); c.arrow((C[0] + C[1] / 2, 0.34), (C[0] + C[1] / 2, 0.32))
    c.box(0.295, 0.165, 0.43, 0.155, "Included  n = 244 records (240 studies)",
          "Scopus 191 + added 53\ncore 144 · supporting 88 · reviews 12\nprimary records (core + supporting) = 232\nfull-text pilot: 4 records, 2 labels changed", fc=LIGHTBLUE)
    c.box(0.07, 0.005, 0.915, 0.14, "Gap-verification probes (OpenAlex, title and abstract; not added to corpus counts)",
          "(a) all three requirements, broadened vocabulary: 6 hits, no primary study\n(b) calibration or conformal terms in CPS / IoT settings: 37 hits (Section 6.4)\n(c) power-system vocabulary with physical-network or physics terms: 242 hits, 29 titles (Section 7.3)",
          fc=CREAM)
    save(c, "Fig1")


# ============================================================ Fig. 3 system model
def fig3():
    c = Canvas(7.4, 5.8)
    tiers = [(0.775, 0.205, "Cloud"), (0.415, 0.345, "Edge"), (0.115, 0.285, "Physical")]
    for y, h, lab in tiers:
        p = FancyBboxPatch((0.03, y), 0.945, h, boxstyle="round,pad=0,rounding_size=0.012", fc="#f4f4f4", ec="#9a9a9a", lw=0.8, zorder=0)
        c.ax.add_patch(p)
        c.text(0.05, y + h / 2, lab + " tier", rotation=90, ha="center", va="center", fontsize=8, style="italic", color=MUTED)
    kx = [0.13, 0.23, 0.33, 0.45, 0.55, 0.65]; ky = 0.475; kr = 0.030
    agg = [(0.13, 0.33), (0.45, 0.55)]          # client ranges served by each edge aggregator
    c.box(0.24, 0.83, 0.20, 0.09, "Cloud aggregator\n(optional)")
    c.box(0.66, 0.83, 0.27, 0.09, "Fleet-level twin / archive")
    c.arrow((0.44, 0.875), (0.66, 0.875), style="<|-|>")
    ax_ = [0.23, 0.50]
    for x in ax_:
        c.box(x - 0.085, 0.61, 0.17, 0.06, "Edge aggregator", tsize=7.6)
        c.arrow((x, 0.67), (0.34 + (x - 0.365) * 0.25, 0.83))
    for i, x in enumerate(kx):
        p = Circle((x, ky), kr, fc="white", ec=INK, lw=1.0, zorder=2); c.ax.add_patch(p)
        t = c.ax.text(x, ky, f"$k_{i + 1}$", ha="center", va="center", fontsize=8.5, zorder=3); c.owned.append((t, p))
    for i in (0, 1, 2):
        c.line([kx[i], ax_[0]], [ky + kr, 0.61])
    for i in (3, 4):
        c.line([kx[i], ax_[1]], [ky + kr, 0.61])
    for i, j in [(2, 3), (4, 5)]:
        c.line([kx[i] + kr, kx[j] - kr], [ky, ky], ls=(0, (4, 2)))
    c.box(0.705, 0.595, 0.26, 0.145, "Edge digital twin", "uses the federated model for\npredictions, uncertainty\nand what-if analyses", fc=LIGHTBLUE)
    c.arrow((0.585, 0.64), (0.705, 0.64), color=BLUE)
    c.text(0.84, 0.515, "communication topology $\\mathcal{G}_c^t$\nsolid: hierarchical links\ndashed: peer-to-peer links\nmixing matrix $\\mathbf{W}^t$", ha="center", va="center", fontsize=7.2, linespacing=1.3)
    c.text(0.84, 0.44, "graph-structured data $\\mathcal{G}_d$ may be\nderived from $\\mathcal{G}_p$ or $\\mathcal{G}_c$", ha="center", va="center", fontsize=6.9, color="#333")
    ay = 0.24
    for i, x in enumerate(kx):
        p = Rectangle((x - 0.03, ay - 0.022), 0.06, 0.044, fc="#fdf3e1", ec=INK, lw=0.9, zorder=2); c.ax.add_patch(p)
        t = c.ax.text(x, ay, f"A{i + 1}", ha="center", va="center", fontsize=7.8, zorder=3); c.owned.append((t, p))
        c.arrow((x, ay + 0.022), (x, ky - kr), color="#555", lw=0.8, ls=(0, (2, 2)), style="<|-|>")
    for i in range(5):
        if i == 2:     # an open switch between A3 and A4
            c.line([kx[i] + 0.03, kx[i] + 0.06], [ay, ay], color=BROWN, lw=2.0)
            c.line([kx[i] + 0.06, kx[i] + 0.085], [ay, ay + 0.02], color=BROWN, lw=2.0)
            c.line([kx[i] + 0.085, kx[i + 1] - 0.03], [ay, ay], color=BROWN, lw=2.0)
        else:
            c.line([kx[i] + 0.03, kx[i + 1] - 0.03], [ay, ay], color=BROWN, lw=2.0)
    c.arrow((kx[1], ay - 0.022), (kx[4], ay - 0.022), color=BROWN, lw=2.0, rad=0.28, style="-")
    c.text(0.385, 0.274, "open switch", ha="center", va="bottom", fontsize=6.5, color=BROWN)
    c.text(0.84, 0.30, "physical / process topology $\\mathcal{G}_p^t$\nfeeders, pipes, process flow;\nswitching changes $\\mathcal{E}_p^t$", ha="center", va="center", fontsize=7.2, color=BROWN, linespacing=1.3)
    c.text(0.84, 0.18, "client-to-node map $\\pi:\\mathcal{V}_p\\to\\mathcal{K}$\n(dashed: sensing and actuation)", ha="center", va="center", fontsize=7.0, color="#333", linespacing=1.3)
    c.arrow((0.05, 0.065), (0.975, 0.065), lw=1.2)
    c.text(0.51, 0.03, "time $t$: client distributions $\\mathcal{D}_k^t$ drift; models adapt and retain; calibration data age; $\\mathcal{G}_c^t$ and $\\mathcal{G}_p^t$ may change",
           ha="center", va="center", fontsize=7.2)
    save(c, "Fig3")


# ============================================================ Fig. 4 taxonomy
def fig4():
    c = Canvas(7.4, 4.9)
    c.box(0.18, 0.88, 0.64, 0.085, "Federated learning for distributed CPS and edge digital twins", fc=LIGHTBLUE, tsize=8.6)
    c.line([0.5, 0.5], [0.88, 0.855]); c.line([0.175, 0.825], [0.855, 0.855])
    cols = [("Continual adaptation (Section 5)", ["Regularisation", "Replay (exemplar, generative)", "Architectural and transfer", "Distillation",
                                                 "Drift detection, adaptive aggregation", "Online streaming FL", "Asynchronous system-aware FCL"]),
            ("Uncertainty (Section 6)", ["Probabilistic and Bayesian", "Sampling-based (MC dropout,\nensembles)", "Evidential, belief functions",
                                         "Conformal (local, pooled,\nadaptive)", "Calibration analysis and trust", "Uncertainty as a control signal"]),
            ("Structure (Section 7)", ["Hierarchical aggregation", "Decentralised mixing,\ntopology design", "Semi-decentralised,\nmulti-server",
                                       "Federated graph learning", "Physical-network-aware", "Physics-consistent\n(residual terms)"])]
    for k, (title, fams) in enumerate(cols):
        x = 0.025 + k * 0.325; w = 0.30
        c.arrow((x + w / 2, 0.855), (x + w / 2, 0.81))
        c.box(x, 0.755, w, 0.055, title, fc="white", tsize=8.0)
        c.line([x + 0.02, x + 0.02], [0.755, 0.71 - (len(fams) - 1) * 0.071], color="#888", lw=0.7)
        for i, f in enumerate(fams):
            yc = 0.71 - i * 0.071
            c.box(x + 0.045, yc - 0.028, w - 0.045, 0.056, None, f, fc=PALE, ec="#999", bsize=6.9, lw=0.7)
            c.line([x + 0.02, x + 0.045], [yc, yc], color="#888", lw=0.7)
    c.box(0.025, 0.012, 0.95, 0.165, "Cross-cutting layer (Sections 3.9, 8, 10 and 11)",
          "Composite objective (9); pairwise tensions: adaptation–calibration, consensus–locality, aggregation–uncertainty\n"
          "Client-to-node map $\\pi$ and time-varying $\\mathcal{G}_p^t$; decision-level online learning; evidence levels E1–E5\n"
          "Reference benchmark: IEEE 33-bus feeder, photovoltaic drift on one lateral, reconfiguration, three communication topologies",
          fc=CREAM, tsize=8.0, bsize=7.0)
    save(c, "Fig4")


# ============================================================ Fig. 5 tensions
def fig5():
    c = Canvas(7.4, 5.0)
    asp = 7.4 / 5.0
    P = {"C": (0.50, 0.70), "U": (0.31, 0.36), "T": (0.69, 0.36)}
    rr = 0.045
    for (a, b) in [("C", "U"), ("C", "T"), ("U", "T")]:
        (x1, y1), (x2, y2) = P[a], P[b]; d = np.hypot((x2 - x1) * asp, y2 - y1)
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        c.line([x1 + ux * rr * 1.05, x2 - ux * rr * 1.05], [y1 + uy * rr * asp * 1.05, y2 - uy * rr * asp * 1.05], color=ORANGE, lw=2.2)
    for k, (x, y) in P.items():
        p = matplotlib.patches.Ellipse((x, y), 2 * rr, 2 * rr * asp, fc=LIGHTBLUE, ec=BLUE, lw=1.4, zorder=2); c.ax.add_patch(p)
        t = c.ax.text(x, y, k, ha="center", va="center", fontsize=15, fontweight="bold", color=BLUE, zorder=3); c.owned.append((t, p))
    c.text(0.50, 0.835, "Continual adaptation\n$F_k^t$, retention $R_C$", ha="center", va="center", fontsize=7.6)
    c.text(0.31, 0.245, "Calibrated uncertainty\n$R_U$, coverage (8)", ha="center", va="center", fontsize=7.6)
    c.text(0.69, 0.245, "Structure\nmixing (5), structural term on $\\mathcal{G}_p^t$", ha="center", va="center", fontsize=7.6)
    c.text(0.50, 0.465, "Composite\nobjective (9):\nno corpus study\ninstantiates all\nthree terms", ha="center", va="center", fontsize=7.0, style="italic", color=MUTED)
    hyp = [("H1  adaptation–calibration", "calibration data lag the drift.\nBenchmark: the lag sits in\nthe recalibrator, not in\nthe model", (0.01, 0.48, 0.285, 0.22), (0.405, 0.53), (0.295, 0.60)),
           ("H2  consensus–locality", "mixing spreads drift-specific\nupdates. Benchmark: the\nfeeder-aligned graph recovers\nfastest at equal spectral gap", (0.705, 0.48, 0.285, 0.22), (0.595, 0.53), (0.705, 0.60)),
           ("H3  aggregation–uncertainty", "averaged models need not be calibrated at any client.\nBenchmark: false alarms at never-alarm zones; pooled\nconformal sets under-cover alarm-prone zones", (0.22, 0.01, 0.56, 0.175), (0.50, 0.36), (0.50, 0.185))]
    for title, body, (x, y, w, h), p_edge, p_box in hyp:
        c.box(x, y, w, h, title, body, fc="white", ec=ORANGE, tsize=7.8, bsize=7.0, lw=0.9)
        c.line([p_edge[0], p_box[0]], [p_edge[1], p_box[1]], color=ORANGE, lw=0.8, ls=(0, (2, 2)))
    save(c, "Fig5")


# ============================================================ Fig. 6 benchmark setup
def fig6():
    import importlib.util
    spec = importlib.util.spec_from_file_location("b", f"{BENCH}/bench_fl.py"); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    zone_of = {bus: k for k, bs in enumerate(b.ZONES) for bus in bs}
    zc = ["#5f8fd0", "#2a78d6", "#1c5cab", "#104281", "#8fb8ec", "#a9c8f0", ORANGE, "#c4501f"]
    c = Canvas(7.4, 6.6)
    dx = 0.048; x0 = 0.09; yT, yU, yL5, yL6 = 0.80, 0.93, 0.66, 0.52
    xy = {i: (x0 + i * dx, yT) for i in range(18)}
    for j, bus in enumerate(range(18, 22)): xy[bus] = (x0 + (1 + j) * dx, yU)
    for j, bus in enumerate(range(22, 25)): xy[bus] = (x0 + (2 + j) * dx, yL5)
    for j, bus in enumerate(range(25, 33)): xy[bus] = (x0 + (5 + j) * dx, yL6)
    lines = [(i, i + 1) for i in range(17)] + [(1, 18), (18, 19), (19, 20), (20, 21), (2, 22), (22, 23), (23, 24), (5, 25)] + [(i, i + 1) for i in range(25, 31)]
    for a, q in lines:
        c.line([xy[a][0], xy[q][0]], [xy[a][1], xy[q][1]], color="#555", lw=1.4)
    c.line([xy[31][0] + 0.012, xy[32][0] - 0.012], [yL6, yL6], color="#555", lw=1.4, ls=(0, (1, 1.5)))      # 31-32, opened at round 225
    # tie line 17-32, routed around the drawing to stay clear of labels
    c.line([xy[17][0] + 0.012, 0.965, 0.965, xy[32][0] + 0.012], [yT, yT, yL6, yL6], color=ORANGE, lw=1.5, ls=(0, (3, 2)))
    r = 0.0125
    for bus, (x, y) in xy.items():
        if bus == 0:
            p = Rectangle((x - 0.014, y - 0.03), 0.028, 0.06, fc=INK, ec=INK, zorder=3); c.ax.add_patch(p)
            c.text(x, y - 0.06, "substation", fontsize=6.6, ha="center", va="top"); continue
        z = zone_of[bus]
        c.ax.add_patch(matplotlib.patches.Ellipse((x, y), 2 * r, 2 * r * 7.4 / 6.6, fc=zc[z], ec="white", lw=0.8, zorder=3))
        if y == yU:
            c.text(x, y + 0.022, str(bus), fontsize=5.8, ha="center", va="bottom", color="#333")
        elif y == yT and bus != 1:
            c.text(x, y + 0.022, str(bus), fontsize=5.8, ha="center", va="bottom", color="#333")
        elif y == yT:
            c.text(x + 0.016, y - 0.02, "1", fontsize=5.8, ha="left", va="top", color="#333")
        else:
            c.text(x, y - 0.022, str(bus), fontsize=5.8, ha="center", va="top", color="#333")
    for bus in range(25, 33):
        c.text(xy[bus][0], yL6 - 0.06, "PV", fontsize=5.6, ha="center", va="top", color="#a76a00", fontweight="bold")
    lab = {0: (np.mean([xy[q][0] for q in b.ZONES[0]]), yT - 0.05), 1: (np.mean([xy[q][0] for q in b.ZONES[1]]), yT - 0.05),
           2: (np.mean([xy[q][0] for q in b.ZONES[2]]), yT - 0.05), 3: (np.mean([xy[q][0] for q in b.ZONES[3]]), yT - 0.05),
           4: (xy[21][0] + 0.05, yU), 5: (xy[22][0] - 0.05, yL5), 6: (np.mean([xy[q][0] for q in b.ZONES[6]]), yL6 - 0.105),
           7: (np.mean([xy[q][0] for q in b.ZONES[7]]), yL6 - 0.105)}
    for z, (x, y) in lab.items():
        c.text(x, y, f"Z{z}", fontsize=8, fontweight="bold", ha="center", va="center", color=zc[z])
    c.text(0.95, 0.655, "tie 17–32 closed at\nround 225; line 31–32\nopened (reconfiguration)", fontsize=6.6, color="#a14217", ha="right", va="center", linespacing=1.3)
    c.text(0.50, 0.375, "Unmetered rooftop PV on buses 25–32 from round 150 (concept drift in Z6, Z7 and, through the trunk, Z1–Z3)", fontsize=6.9, color="#a14217", ha="center", va="center")
    # communication graphs drawn on the physical layout of the zones
    pos = {0: (0.0, 0.0), 1: (1.0, 0.0), 2: (2.0, 0.0), 3: (3.0, 0.0), 4: (0.5, 0.9), 5: (1.0, -0.9), 6: (2.0, -0.9), 7: (3.0, -0.9)}
    graphs = [("Feeder-aligned peer-to-peer", b.ZONE_TREE, None), ("Misaligned peer-to-peer\n(same tree, relabelled)", b.TOPOLOGIES["misaligned"], None),
              ("Star (FedAvg server S)", [("S", i) for i in range(8)], (1.5, 0.1))]
    circles = []
    for g, (title, edges, hub) in enumerate(graphs):
        a2 = c.fig.add_axes([0.02 + g * 0.33, 0.02, 0.30, 0.33]); a2.axis("off"); a2.set_xlim(-0.55, 3.55); a2.set_ylim(-1.75, 1.45); a2.set_aspect("equal", adjustable="datalim")
        P = dict(pos)
        if hub:
            ang = np.linspace(0, 2 * np.pi, 9)[:-1] + np.pi / 2
            P = {i: (1.5 + 0.95 * np.cos(t), 0.1 + 0.95 * np.sin(t)) for i, t in enumerate(ang)}; P["S"] = hub
        drawn = []
        def curve(i, j, rad):
            (x1, y1), (x2, y2) = P[i], P[j]
            cx, cy = (x1 + x2) / 2 + rad * (y2 - y1), (y1 + y2) / 2 - rad * (x2 - x1)
            tt = np.linspace(0, 1, 60)[:, None]
            return (1 - tt) ** 2 * np.array([x1, y1]) + 2 * (1 - tt) * tt * np.array([cx, cy]) + tt ** 2 * np.array([x2, y2])
        def clearance(i, j, rad):
            pts = curve(i, j, rad); inner = pts[8:-8]
            d = [np.min(np.hypot(*(inner - np.array(P[k])).T)) for k in P if k not in (i, j)]
            for (a_, b_), q in drawn:
                if {a_, b_} & {i, j}: continue
                d.append(np.min(np.hypot(inner[:, None, 0] - q[None, 8:-8, 0], inner[:, None, 1] - q[None, 8:-8, 1])) + 0.05)
            return min(d) if d else 9
        for i, j in edges:
            rad = 0.0 if clearance(i, j, 0.0) >= 0.35 else max([-0.3, 0.3, -0.5, 0.5], key=lambda r: (min(clearance(i, j, r), 0.45), -abs(r)))
            drawn.append(((i, j), curve(i, j, rad)))
            a = FancyArrowPatch(P[i], P[j], arrowstyle="-", lw=1.0, color=INK, connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0, zorder=1)
            a2.add_patch(a); c.conn.append(a)
        for i, (x, y) in P.items():
            if i == "S":
                p = Circle((x, y), 0.22, fc="white", ec=INK, lw=1.0, zorder=2); a2.add_patch(p)
                t = a2.text(x, y, "S", ha="center", va="center", fontsize=6.8, zorder=3); c.owned.append((t, p))
                circles.append((x, y, 0.22, a2.transData, "S")); continue
            p = Circle((x, y), 0.25, fc=zc[i], ec="white", lw=1.0, zorder=2); a2.add_patch(p)
            t = a2.text(x, y, f"Z{i}", ha="center", va="center", fontsize=6.4, color="white" if i not in (4, 5) else INK, zorder=3)
            c.owned.append((t, p)); circles.append((x, y, 0.25, a2.transData, f"Z{i}"))
        t = a2.text(1.5, -1.3, title, ha="center", va="top", fontsize=7.2); c.free.append(t)
    qa(c.fig, c.owned, c.free, c.conn, circles=circles, name="Fig6", pad=1.0)
    c.fig.savefig(f"{OUT}/Fig6.png", dpi=300); plt.close(c.fig)


# ============================================================ Fig. 7 benchmark time series
def fig7():
    S = np.load(f"{BENCH}/results/series.npz")
    rounds = np.arange(100, 300)
    cfgs = [("star", BLUE, "-"), ("aligned", AQUA, "-"), ("misaligned", ORANGE, "--"), ("local", YELLOW, ":")]
    names = {"star": "star (FedAvg)", "aligned": "feeder-aligned", "misaligned": "misaligned", "local": "local only"}
    fig, axs = plt.subplots(3, 1, figsize=(7.2, 7.2), sharex=True)
    for ax, mk, lab in [(axs[0], "err", "Error\n(drifted zones)"), (axs[1], "ece", "ECE\n(drifted zones)")]:
        for t, col, ls in cfgs:
            arr = S[f"{t}|W24|current::{mk}"]; m = np.nanmean(arr, 0); s = np.nanstd(arr, 0)
            ax.plot(rounds, m, color=col, lw=1.7, ls=ls, label=names[t]); ax.fill_between(rounds, m - s, m + s, color=col, alpha=0.12, lw=0)
        ax.set_ylabel(lab); ax.set_ylim(bottom=0)
    axs[0].legend(frameon=False, ncol=4, fontsize=7.4, loc="lower center", bbox_to_anchor=(0.5, 1.12))
    for mk, col, ls, lab in [("cov_ps", BLUE, "-", "pooled, static calibration"), ("cov_pw", ORANGE, "--", "pooled, sliding window"), ("cov_lw", AQUA, "-", "per-client, sliding window")]:
        arr = S[f"star|W24|current::{mk}"]; axs[2].plot(rounds, np.nanmean(arr, 0), color=col, lw=1.5, ls=ls, label=lab)
    axs[2].axhline(0.9, color=INK, lw=0.8, ls=":", label="target coverage 0.90")
    axs[2].set_ylabel("Coverage, star\n(drifted zones)"); axs[2].set_ylim(0.5, 1.02)
    axs[2].legend(frameon=False, fontsize=7.0, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.32))
    for ax in axs:
        for r0 in (150, 225):
            ax.axvline(r0, color="#888", lw=0.9, ls="--")
        ax.yaxis.grid(True, color="#eeeeee", lw=0.6); ax.set_axisbelow(True)
    for r0, lab in [(150, "PV onset"), (225, "reconfiguration")]:
        axs[0].annotate(lab, xy=(r0, 1.0), xycoords=("data", "axes fraction"), xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7, color=MUTED)
    axs[2].set_xlabel("Communication round (1 round = 1 h of operation)"); axs[2].set_xlim(98, 302); axs[2].set_xticks(range(100, 301, 25))
    fig.tight_layout(); fig.subplots_adjust(top=0.90)
    fig.canvas.draw(); r = fig.canvas.get_renderer()
    fb = fig.bbox
    for t in fig.findobj(matplotlib.text.Text):
        if t.get_text().strip() and t.get_visible():
            bb = t.get_window_extent(r)
            if bb.x0 < fb.x0 - 1 or bb.x1 > fb.x1 + 1 or bb.y0 < fb.y0 - 1 or bb.y1 > fb.y1 + 1:
                raise RuntimeError(f"Fig7: text clipped {t.get_text()!r}")
    print("Fig7: no text clipped at the figure edge")
    fig.savefig(f"{OUT}/Fig7.png", dpi=300); plt.close(fig)


# ============================================================ Fig. 8 per-client coverage and calibration
def fig8():
    import pandas as pd
    P = pd.read_csv(f"{BENCH}/results/per_client_metrics.csv")
    q = P[(P.config == "star|W24|current") & (P.phase == "pre")]
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.4))
    z = np.arange(8); w = 0.36
    for mk, col, lab, off, hatch in [("cov_ps", BLUE, "pooled calibration", -w / 2, None), ("cov_lw", AQUA, "per-client calibration", w / 2, "///")]:
        g = q[q.metric == mk].groupby("zone").value
        axs[0].bar(z + off, g.mean().values, w, yerr=g.std().values, color=col, label=lab, edgecolor="white", linewidth=1, hatch=hatch, error_kw=dict(lw=0.8, capsize=2))
    axs[0].axhline(0.9, color=INK, lw=0.8, ls=":"); axs[0].set_ylim(0.6, 1.04)
    axs[0].set_ylabel("Coverage before drift"); axs[0].set_title("Split conformal sets, $\\alpha = 0.10$ (star, $H = 24$)", fontsize=8.2)
    for mk, col, lab, off, hatch in [("ece", BLUE, "global model", -w / 2, None), ("ece_ts_sliding", AQUA, "+ per-client temperature", w / 2, "///")]:
        g = q[q.metric == mk].groupby("zone").value
        axs[1].bar(z + off, g.mean().values, w, yerr=g.std().values, color=col, label=lab, edgecolor="white", linewidth=1, hatch=hatch, error_kw=dict(lw=0.8, capsize=2))
    axs[1].set_ylabel("ECE before drift"); axs[1].set_title("Per-client calibration of the global model", fontsize=8.2)
    for ax in axs:
        ax.set_xticks(z); ax.set_xticklabels([f"Z{i}" for i in z])
        ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
        ax.yaxis.grid(True, color="#eeeeee", lw=0.6); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(f"{OUT}/Fig8.png", dpi=300); plt.close(fig)
    print("Fig8: saved")


if __name__ == "__main__":
    which = sys.argv[2:] or ["6", "7", "8"]
    for k in which:
        try:
            globals()[f"fig{k}"]()
        except RuntimeError as e:
            print("FAILED", e)
