"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben."""

import plotly.graph_objects as go

import vdw_constants as C
from vdw_evaluation import de


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=360, legend=True):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="rgba(0,0,0,0)", showlegend=legend,
                      legend=dict(orientation="h", y=-0.25))
    return lock_axes(fig)


def build_raster(matrix, ms, ws, title, zmax=12.0):
    """Heatmap Lücke in % der exakten Kosten (Zeilen: w, Spalten: Haltbarkeit); `matrix[i][j]` gehört zu ws[i], ms[j], None = nicht gerechnet."""
    text = [["" if v is None else de(max(v, 0.0), 2) for v in row] for row in matrix]
    z = [[None if v is None else min(max(v, 0.0), zmax) for v in row] for row in matrix]
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{m}" for m in ms], y=[de(w, 0) for w in ws], text=text, texttemplate="%{text}", colorscale="YlOrRd", zmin=0, zmax=zmax,
        colorbar=dict(title=f"% (bis {zmax:g})"), hovertemplate="Haltbarkeit %{x}, w = %{y}: %{text} %<extra></extra>", xgap=2, ygap=2))
    fig.update_xaxes(title_text="Haltbarkeit m (Perioden)", type="category")
    fig.update_yaxes(title_text="Verfallskosten w", type="category")
    fig.update_layout(title=dict(text=title, font=dict(size=14)))
    return _base(fig, height=330, legend=False)


def build_statespace(rows):
    """Zustandszahlen je Haltbarkeit (logarithmisch): Kasten, alle Zustände, erreichbar bei beliebiger Bestellung, unter der DP, unter dem Base-Stock."""
    ms = [str(r["m"]) for r in rows]
    fig = go.Figure()
    for key, name, color in (("box", "Kasten (T+1)^k", "#c9c9c9"), ("states", "Zustände C(T+k, k)", C.COLOR_FIFO), ("reach_dp", "erreichbar unter der DP", C.COLOR_DP),
                             ("reach_bs", "erreichbar unter Base-Stock", C.COLOR_BS)):
        fig.add_trace(go.Bar(x=ms, y=[r[key] for r in rows], name=name, marker_color=color, hovertemplate=f"{name}: %{{y:,}}<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(type="log", title_text="Zahl der Zustände")
    fig.update_xaxes(title_text="Haltbarkeit m (Perioden)", type="category")
    return _base(fig, height=380)


def build_targets(table, max_tot=None):
    """Heatmap: Auffüllziel (Gesamtbestand + Bestellung) der exakten Politik nach Gesamtbestand (x) und Menge der ältesten Klasse z1 (y);
    `table`: {(Gesamtbestand, z1): (Ziel, eindeutig)}. Zellen mit unterschiedlichen Zielen bei gleichem Schlüssel tragen ein Sternchen."""
    if not table:
        return None
    tots = sorted({k[0] for k in table})
    z1s = sorted({k[1] for k in table})
    z = [[None for _ in tots] for _ in z1s]
    text = [["" for _ in tots] for _ in z1s]
    for (t, z1), (tgt, unique) in table.items():
        z[z1s.index(z1)][tots.index(t)] = tgt
        text[z1s.index(z1)][tots.index(t)] = f"{tgt}" + ("" if unique else "*")
    fig = go.Figure(go.Heatmap(z=z, x=[str(t) for t in tots], y=[str(v) for v in z1s], text=text, texttemplate="%{text}", colorscale="Blues",
                               colorbar=dict(title="Ziel"), hovertemplate="Bestand %{x}, älteste Klasse %{y}: Ziel %{text}<extra></extra>", xgap=2, ygap=2))
    fig.update_xaxes(title_text="Gesamtbestand vor der Bestellung", type="category")
    fig.update_yaxes(title_text="älteste Klasse z₁", type="category")
    return _base(fig, height=340, legend=False)


def build_gap_bars(cell):
    """Lücke zur exakten Politik (in %) für Base-Stock, Altersregel, Tabelle nach Gesamtbestand und Tabelle nach Gesamtbestand und z1 (soweit gerechnet)."""
    items = [("Base-Stock auf Gesamtbestand", cell["gap_bs"], C.COLOR_BS)]
    if "gap_age" in cell:
        items.append(("Altersregel S + β·z₁", cell["gap_age"], C.COLOR_RULE))
        items.append(("Tabelle a(Gesamtbestand)", cell["gap_tab_total"], C.COLOR_TAB))
    if cell.get("gap_tab_total_z1") is not None:
        items.append(("Tabelle a(Gesamtbestand, z₁)", cell["gap_tab_total_z1"], C.COLOR_TAB_Z1))
    vals = [max(v, 0.0) for _, v, _ in items]
    fig = go.Figure(go.Bar(x=[n for n, _, _ in items], y=vals, marker_color=[c for _, _, c in items], text=[de(v, 2) + " %" for v in vals], textposition="outside",
                           hovertemplate="%{x}: %{y:.2f} %<extra></extra>"))
    fig.update_yaxes(title_text="Lücke zur exakten Politik (%)", rangemode="tozero")
    return _base(fig, height=340, legend=False)


def build_age_grid(grid, betas, current, zmax=15.0):
    """Heatmap der Lücke der Altersregel über beta (y) und S (x); der gewählte Punkt ist markiert."""
    levels = list(range(len(grid[0])))
    z = [[min(max(v, 0.0), zmax) for v in row] for row in grid]
    text = [[de(max(v, 0.0), 1) for v in row] for row in grid]
    fig = go.Figure(go.Heatmap(z=z, x=[str(s) for s in levels], y=[de(b, 2, True) for b in betas], text=text, texttemplate="%{text}", colorscale="YlOrRd", zmin=0, zmax=zmax,
                               colorbar=dict(title=f"% (bis {zmax:g})"), hovertemplate="S = %{x}, β = %{y}: %{text} %<extra></extra>", xgap=1, ygap=1))
    s, b = current
    fig.add_trace(go.Scatter(x=[str(s)], y=[de(b, 2, True)], mode="markers", marker=dict(symbol="square-open", size=22, color="#111", line=dict(width=3)),
                             name="gewählt", hoverinfo="skip"))
    fig.update_xaxes(title_text="Niveau S", type="category")
    fig.update_yaxes(title_text="β", type="category")
    return _base(fig, height=520, legend=False)


def build_decomposition(rows):
    """Gestapelte Kostenzerlegung: Lager h (y-d)^+, Fehlmenge p (d-y)^+, Verfall (w-h) mal Ablaufmenge; `rows`: Liste (Beschriftung, Terme)."""
    labels = [r[0] for r in rows]
    fig = go.Figure()
    for key, name, color in (("lager", "Lager: h · (y − d)⁺", C.COLOR_H), ("fehl", "Fehlmenge: p · (d − y)⁺", C.COLOR_P), ("verfall", "Verfall: (w − h) · Ablaufmenge", C.COLOR_W)):
        fig.add_trace(go.Bar(x=labels, y=[r[1][key] for r in rows], name=name, marker_color=color, hovertemplate=f"{name}: %{{y:.4f}}<extra></extra>"))
    fig.update_layout(barmode="relative")
    fig.add_trace(go.Scatter(x=labels, y=[r[1]["summe"] for r in rows], mode="markers+text", text=[de(r[1]["summe"], 4) for r in rows], textposition="top center",
                             marker=dict(symbol="diamond", size=10, color="#111"), name="Summe = Kosten je Periode", hoverinfo="skip"))
    fig.update_yaxes(title_text="Kosten je Periode")
    return _base(fig, height=420)
