"""Einfache Bestellregeln für den Altersvektor und ihr Abstand zur exakten DP.

Familien (alle werden mit der exakten Auswertung `Perishable.evaluate` bewertet):
  Base-Stock        Auffüllen auf S, gemessen am Gesamtbestand (ein Parameter)
  Altersregel       Auffüllen auf S + beta * z1 (z1 = Menge der ältesten Klasse), gerundet; zwei Parameter
  Tabelle f(Bestand)        beste Bestellmenge je Gesamtbestand (Koordinatenabstieg, lokales Optimum)
  Tabelle f(Bestand, z1)    beste Bestellmenge je (Gesamtbestand, älteste Klasse)
Der Koordinatenabstieg probiert je Schlüssel alle zulässigen Bestellmengen und übernimmt die beste, bis eine Runde nichts ändert. Er findet ein
lokales Optimum, keinen Beweis des globalen; die Ergebnisse sind obere Schranken für die beste Tabelle.
"""

from __future__ import annotations

import numpy as np

BETAS = tuple(float(b) for b in np.arange(-2.0, 1.01, 0.25))   # Raster der Altersregel: -2 bis +1 in Vierteln


def age_target(P, level: int, beta: float) -> np.ndarray:
    """Auffüllziel S + beta * z1, auf ganze Stück gerundet (halbe nach oben)."""
    return np.floor(level + beta * P.z1.astype(float) + 0.5)


def age_policy(P, level: int, beta: float) -> np.ndarray:
    """Bestellmenge der Altersregel: Ziel minus Gesamtbestand, nie negativ, auf das Zulässige gekappt durch `Perishable.eff`."""
    return np.clip(age_target(P, level, beta) - P.tot, 0, P.cfg.T).astype(int)


def best_age_rule(P, betas=BETAS):
    """Beste Altersregel (Kosten, S, beta); beta = 0 ist der Base-Stock."""
    best = (np.inf, None, None)
    for beta in betas:
        for level in range(0, P.cfg.T + 1):
            g, _ = P.evaluate(age_policy(P, level, beta))
            if g < best[0] - 1e-12:
                best = (g, level, beta)
    return best


def best_without_oldest(P):
    """Base-Stock auf dem Bestand ohne die älteste Klasse (beta = +1 ohne Rundungsfall): (Kosten, S)."""
    best = (np.inf, None)
    for level in range(0, P.cfg.T + 1):
        g, _ = P.evaluate(P.position_rule(level, P.tot - P.z1))
        if g < best[0]:
            best = (g, level)
    return best


def coordinate_descent(P, key: np.ndarray, start_pol: np.ndarray, max_rounds: int = 20, tol: float = 1e-12):
    """Beste Politik, die nur vom Schlüssel (ganzzahliger Vektor je Zustand) abhängt. Rückgabe: (Kosten, Politik, Runden)."""
    keys = np.unique(key)
    pol = start_pol.copy()
    g, pi = P.evaluate(pol)
    rnd = 0
    for rnd in range(max_rounds):
        changed = False
        mass = np.array([pi[key == kk].sum() for kk in keys])        # Reihenfolge: absteigende Masse unter der aktuellen Politik
        for kk in keys[np.argsort(-mass)]:
            sel = key == kk
            amax = int(P.amax[sel].min())
            cur = int(pol[sel][0])
            best_a, best_g = cur, g
            for a in range(0, max(amax, 0) + 1):
                if a == cur:
                    continue
                trial = pol.copy()
                trial[sel] = a
                g2, _ = P.evaluate(trial)
                if g2 < best_g - tol:
                    best_a, best_g = a, g2
            if best_a != cur:
                pol[sel] = best_a
                g, pi = P.evaluate(pol)
                changed = True
        if not changed:
            break
    return g, pol, rnd + 1


def best_table_by_total(P, dp_pol: np.ndarray, dp_pi: np.ndarray, bs_pol: np.ndarray):
    """Beste Tabelle f(Gesamtbestand): zwei Starts (Base-Stock und die nach Gesamtbestand gemittelte DP-Politik), der bessere zählt."""
    g1, _, _ = coordinate_descent(P, P.tot, bs_pol)
    ae = P.eff(dp_pol)
    supp = dp_pi > 1e-9
    proj = bs_pol.copy()
    for tt in np.unique(P.tot):
        sel = (P.tot == tt) & supp
        if sel.any():
            vals = np.unique(ae[sel])
            mass = {int(v): dp_pi[sel & (ae == v)].sum() for v in vals}
            proj[P.tot == tt] = max(mass, key=mass.get)
    proj = np.minimum(proj, P.amax)
    g2, _, _ = coordinate_descent(P, P.tot, proj)
    return min(g1, g2)


def best_table_by_total_and_oldest(P, bs_pol: np.ndarray):
    """Beste Tabelle f(Gesamtbestand, älteste Klasse), Start Base-Stock."""
    key = P.tot * 100 + P.z1
    g, _, _ = coordinate_descent(P, key, bs_pol)
    return g


def ambiguity(P, ae: np.ndarray, supp: np.ndarray, key_fn) -> tuple[int, int]:
    """(Zahl der Schlüssel, unter denen die DP verschieden bestellt, Zahl der Schlüssel) auf den erreichbaren Zuständen."""
    seen: dict = {}
    for s in np.flatnonzero(supp):
        seen.setdefault(key_fn(s), set()).add(int(ae[s]))
    return sum(1 for v in seen.values() if len(v) > 1), len(seen)


def target_table(P, pol: np.ndarray, pi: np.ndarray, min_mass: float = 1e-4):
    """Auffüllziel (Gesamtbestand + Bestellung) je (Gesamtbestand, älteste Klasse) auf den Zuständen mit Masse über `min_mass`.

    Rückgabe: Wörterbuch {(Gesamtbestand, z1): (Ziel, eindeutig)}; bei mehreren Zuständen mit gleichem Schlüssel gilt das Ziel mit der
    größten Masse, `eindeutig` ist False, wenn die Ziele sich unterscheiden."""
    ae = P.eff(pol)
    groups: dict = {}
    for s in np.flatnonzero(pi > min_mass):
        key = (int(P.tot[s]), int(P.z1[s]))
        groups.setdefault(key, {})
        tgt = int(P.tot[s] + ae[s])
        groups[key][tgt] = groups[key].get(tgt, 0.0) + float(pi[s])
    return {key: (max(d, key=d.get), len(d) == 1) for key, d in groups.items()}
