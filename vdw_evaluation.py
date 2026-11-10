"""Kennzahlen, Verdikte (reine Funktionen) und die Live-Rechnung der App.

Jedes Verdikt ist `verdict_*(...) -> (Art, Text)`; die App ruft `getattr(st, Art)(Text)`, `tests/test_verdicts.py` prüft Schwellen und jede Zahl
im Text an handgesetzten Zellen. Zellen sind die Wörterbücher aus `vdw_grid`."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

import numpy as np

import vdw_algorithm as A
import vdw_rules as R

EXACT_GAP = 0.005          # Lücke in %, unter der der Base-Stock als exakt gilt (zusammen mit Q-Abstand 0)
EXACT_Q = 1e-9
SMALL_GAP = 0.5            # Marke „klein“ für die Tabellen und die Altersregel (Prozent der DP-Kosten)


# ------------------------------------------------------------------------------------------------------------------------------ Formatierung
def de(x: float, nd: int = 2, sign: bool = False) -> str:
    """Zahl mit Dezimalkomma; `sign` setzt ein Vorzeichen. Negative Nullen (-0,00) werden zu 0,00."""
    s = f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"
    if float(s) == 0.0:
        s = s.lstrip("+-")
        if sign:
            s = "+" + s
    return s.replace(".", ",")


def de_int(n: int) -> str:
    """Ganzzahl mit Punkt als Tausendertrenner."""
    return f"{n:,}".replace(",", ".")


def frac_text(x: Fraction) -> str:
    return str(x)


# ------------------------------------------------------------------------------------------------------------------------------ Zellen
def is_exact(cell: dict) -> bool:
    """Base-Stock exakt: Lücke unter 0,005 % und Q-Abstand 0 auf allen vom Base-Stock erreichten Zuständen."""
    return cell["gap_bs"] < EXACT_GAP and cell["qgap_max"] < EXACT_Q


def share_closed(cell: dict) -> float | None:
    """Anteil der Base-Stock-Lücke, den die beste Altersregel schließt (in %), oder None, wenn es nichts zu schließen gibt (Lücke unter 0,05 %)."""
    if "gap_age" not in cell or cell["gap_bs"] <= 0.05:
        return None
    return 100.0 * (1.0 - max(cell["gap_age"], 0.0) / cell["gap_bs"])


def cost_terms(comp: dict, p: float, w: float, h: float = 1.0) -> dict:
    """Zerlegung der Periodenkosten: h (y - d)^+ (Lager), p (d - y)^+ (Fehlmenge), (w - h) mal Ablaufmenge; ihre Summe sind die Kosten."""
    lager = h * (comp["carry"] + comp["waste"])
    fehl = p * comp["lost"]
    verfall = (w - h) * comp["waste"]
    return {"lager": lager, "fehl": fehl, "verfall": verfall, "summe": lager + fehl + verfall}


# ------------------------------------------------------------------------------------------------------------------------------ Verdikte
def _label(cell: dict) -> str:
    return f"Haltbarkeit {cell['m']}, w = {de(cell['w'], 0)}"


def verdict_headline(cell: dict) -> tuple[str, str]:
    """Kernfrage: Reicht der Gesamtbestand? Bezugsgröße der Lücke sind die Kosten je Periode der exakten Politik."""
    gap = max(cell["gap_bs"], 0.0)
    head = f"Beste Base-Stock-Regel auf dem Gesamtbestand: S = {cell['S_bs']}, Kosten {de(cell['g_bs'], 4)} je Periode gegen {de(cell['g'], 4)} der exakten Politik."
    if is_exact(cell):
        return "success", (f"{head} Die Regel ist hier **exakt optimal** (Lücke {de(gap)} % der exakten Kosten, Q-Abstand 0 auf allen {cell['reach_bs']} Zuständen, "
                           "die sie erreicht): das Alter der Ware wird hier nicht gebraucht.")
    if gap < 1.0:
        return "info", f"{head} Lücke **{de(gap, 2, True)} %** der exakten Kosten: klein, aber nicht null."
    text = f"{head} Lücke **{de(gap, 2, True)} %** der exakten Kosten."
    share = share_closed(cell)
    if share is not None:
        text += f" Eine Regel mit der Menge der ältesten Klasse (S + β·z₁) schließt davon {de(share, 0)} % (Reiter „Altersregel“)."
    return "warning", text


def verdict_raster(cells: list[dict], metric: str = "gap_bs", name: str = "Base-Stock") -> tuple[str, str]:
    """Zählung über die angezeigten Zellen. Für den Base-Stock: exakt = Lücke unter 0,005 % und Q-Abstand 0; sonst Zellen unter 0,5 %."""
    shown = [c for c in cells if c.get(metric) is not None]
    if not shown:
        return "info", "Für diese Auswahl ist nichts gerechnet."
    n = len(shown)
    if metric == "gap_bs":
        exact = [c for c in shown if is_exact(c)]
        rest = [c for c in shown if not is_exact(c)]
        if not rest:
            return "success", f"{name}: in **{n} von {n} Zellen exakt** (Lücke unter 0,005 %, Q-Abstand 0)."
        worst = max(rest, key=lambda c: c["gap_bs"])
        exc = "; ".join(f"{_label(c)}: {de(max(c['gap_bs'], 0.0), 2, True)} %" for c in sorted(rest, key=lambda c: (c["m"], c["w"]))[:6])
        more = f" (und {len(rest) - 6} weitere)" if len(rest) > 6 else ""
        kind = "info" if exact else "warning"
        return kind, (f"{name}: in **{len(exact)} von {n} Zellen exakt** (Lücke unter 0,005 %, Q-Abstand 0). Größte Lücke {de(worst['gap_bs'], 2, True)} % "
                      f"({_label(worst)}). Übrige Zellen: {exc}{more}.")
    small = [c for c in shown if c[metric] < SMALL_GAP]
    worst = max(shown, key=lambda c: c[metric])
    kind = "success" if len(small) == n else ("info" if small else "warning")
    return kind, (f"{name}: in **{len(small)} von {n} Zellen unter {de(SMALL_GAP, 1)} %** der exakten Kosten. Größte Lücke {de(worst[metric], 2, True)} % "
                  f"({_label(worst)}).")


def verdict_statespace(cell: dict) -> tuple[str, str]:
    share = 100.0 * cell["reach_dp"] / cell["states"]
    return "info", (f"Haltbarkeit {cell['m']}, Lieferzeit {cell['lead']}: **{de_int(cell['states'])} Zustände** (Kasten ohne Gesamtgrenze: {de_int(cell['box'])}). "
                    f"Unter der exakten Politik werden **{de_int(cell['reach_dp'])}** erreicht ({de(share, 1)} % der Zustände), unter dem besten Base-Stock {de_int(cell['reach_bs'])}, "
                    f"bei beliebiger Bestellung {de_int(cell['reach_any'])}.")


def verdict_tables(cell: dict) -> tuple[str, str]:
    """Welche Information braucht die Bestellung? Vergleich der besten Tabellen (obere Schranken aus lokaler Suche) mit dem Base-Stock."""
    if "gap_tab_total" not in cell:
        return "info", "Für diese Zelle sind die Tabellen nicht vorgerechnet; sie gelten nur bis Haltbarkeit 4 (Lieferzeit 0 auch 5)."
    base = f"Lücke zur exakten Politik: Base-Stock {de(max(cell['gap_bs'], 0.0), 2, True)} %, beste Tabelle nach Gesamtbestand {de(max(cell['gap_tab_total'], 0.0), 2, True)} %"
    z1 = cell.get("gap_tab_total_z1")
    if z1 is not None:
        base += f", beste Tabelle nach Gesamtbestand und älteste Klasse {de(max(z1, 0.0), 2, True)} %"
    base += "."
    if cell["gap_tab_total"] < SMALL_GAP:
        return "success", f"{base} Eine Tabelle nur nach dem Gesamtbestand liegt unter {de(SMALL_GAP, 1)} %: das Alter bringt hier höchstens diesen Rest."
    if z1 is not None and z1 < cell["gap_tab_total"] / 2:
        return "info", f"{base} Die älteste Klasse senkt die Lücke der Gesamtbestand-Tabelle mehr als auf die Hälfte."
    return "warning", f"{base} Auch mit den vorgerechneten Tabellen bleibt eine Lücke über {de(SMALL_GAP, 1)} %."


def verdict_age_rule(cell: dict | None, gap_chosen: float | None = None) -> tuple[str, str]:
    """Verdikt zur Altersregel S + β·z₁: Anteil der Base-Stock-Lücke, den die beste Regel (und die gewählte) schließt."""
    if cell is None or "gap_age" not in cell:
        return "info", "Für diese Zelle ist die Altersregel nicht gerechnet."
    share = share_closed(cell)
    best = f"Beste Regel: S = {cell['age_S']}, β = {de(cell['age_beta'], 2, True)}, Lücke {de(max(cell['gap_age'], 0.0), 2, True)} % gegen {de(max(cell['gap_bs'], 0.0), 2, True)} % beim Base-Stock."
    rand = " Das beste β liegt am Rand des Rasters (−2)." if cell["age_beta"] <= -2.0 else ""
    if share is None:
        return "info", f"{best} Der Base-Stock hat hier keine nennenswerte Lücke (unter 0,05 %): es gibt nichts zu schließen.{rand}"
    chosen = ""
    if gap_chosen is not None:
        chosen = f" Die gewählten Werte liegen {de(max(gap_chosen, 0.0), 2, True)} % über der exakten Politik."
    kind = "success" if share >= 90 else "info"
    return kind, f"{best} Das schließt **{de(share, 0)} %** der Base-Stock-Lücke.{chosen}{rand}"


def verdict_decomposition(cf: dict, cl: dict) -> tuple[str, str]:
    """FIFO gegen LIFO bei gleicher Zelle (Lieferzeit, Haltbarkeit, w, p): exakte Kosten und Ablaufmenge unter dem besten Base-Stock."""
    gf, gl = cf["g"], cl["g"]
    wf, wl = cf["bs"]["waste"], cl["bs"]["waste"]
    waste = f"Erwartete Ablaufmenge je Periode unter dem jeweils besten Base-Stock: FIFO {de(wf, 4)}, LIFO {de(wl, 4)}."
    if abs(gl - gf) < 1e-8:
        why = (" Bei w = h und Lieferzeit 0 hängen die Kosten nur vom Bestand nach der Bestellung ab, nicht vom Alter." if cf["lead"] == 0 and cf["w"] == 1.0 else "")
        return "success", f"Exakte Kosten FIFO und LIFO sind **gleich** ({de(gf, 4)} je Periode).{why} {waste}"
    diff = 100.0 * (gl / gf - 1.0)
    if cf["w"] == 0:
        return "info", (f"Bei w = 0 ist LIFO **{de(-diff, 1)} % billiger** als FIFO (Bezug: exakte Kosten FIFO): ablaufende Ware kostet nichts, übertragene h. "
                        f"Das ist eine Folge der Kostenkonvention, keine Aussage über Frischware. {waste}")
    richtung = "über" if diff >= 0 else "unter"
    return "warning", f"Exakte Kosten LIFO liegen **{de(abs(diff), 1)} %** {richtung} denen von FIFO (Bezug: exakte Kosten FIFO, {de(gf, 4)} je Periode). {waste}"


def verdict_hand(summ_fifo: dict, summ_lifo: dict) -> tuple[str, str]:
    """Handbeispiel in Brüchen: Optimum und bester Base-Stock je Ausgaberegel."""
    f, l = summ_fifo, summ_lifo
    gap_l = 100.0 * float(l["gap"])
    return "info", (f"FIFO: Optimum a = {l_tuple(f['opt_policy'])} mit Kosten {f['opt_cost']} je Periode; der beste Base-Stock ({f['bs_cost']}) ist gleich gut. "
                    f"LIFO: Optimum a = {l_tuple(l['opt_policy'])} mit {l['opt_cost']}, der beste Base-Stock kostet {l['bs_cost']}: **{de(gap_l, 2, True)} %** mehr (Bezug: Optimum LIFO).")


def l_tuple(t) -> str:
    return "(" + ", ".join(str(x) for x in t) + ")"


# ------------------------------------------------------------------------------------------------------------------------------ Live-Rechnung
@dataclass
class Live:
    P: A.Perishable
    g: float
    pol: np.ndarray
    h: np.ndarray
    pi: np.ndarray
    cert: float
    level: int
    g_bs: float
    pi_bs: np.ndarray


def solve_live(lead: int, rule: str, w: float, m: int, p: float = 9.0, T: int = 12) -> Live:
    """Exakte DP und bester Base-Stock der Zelle (nur für Zellen bis 1.820 Zustände gedacht)."""
    P = A.Perishable(A.Settings(m=m, lead=lead, rule=rule, w=w, p=p, T=T))
    g, pol, h, _, cert = P.solve()
    _, pi = P.evaluate(pol)
    g_bs, level, pi_bs = P.best_base_stock()
    return Live(P, g, pol, h, pi, cert, level, g_bs, pi_bs)


def age_grid(live: Live, betas=R.BETAS) -> np.ndarray:
    """Lücke (in % der exakten Kosten) der Altersregel auf dem Raster beta x S (169 exakte Auswertungen)."""
    P = live.P
    out = np.empty((len(betas), P.cfg.T + 1))
    for i, beta in enumerate(betas):
        for level in range(P.cfg.T + 1):
            g, _ = P.evaluate(R.age_policy(P, level, beta))
            out[i, level] = 100.0 * (g / live.g - 1.0)
    return out


def age_gap(live: Live, level: int, beta: float) -> float:
    g, _ = live.P.evaluate(R.age_policy(live.P, level, beta))
    return 100.0 * (g / live.g - 1.0)
