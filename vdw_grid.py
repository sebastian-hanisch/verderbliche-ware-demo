"""Vorgerechnetes Raster: Erzeugung (Kommandozeile) und Zugriff (App, Tests).

Je Zelle (Lieferzeit, Ausgaberegel, Verfallskosten w, Strafverhältnis p, Haltbarkeit m, Bestandsgrenze T) wird gerechnet: exakte DP,
bester Base-Stock auf dem Gesamtbestand, Q-Abstand seiner Aktion auf den von ihm erreichten Zuständen (0 heißt: auf allen erreichbaren Zuständen
bestellt die DP dasselbe), Zustandszahlen (Kasten, alle, erreichbar unter DP und unter Base-Stock), Randmasse, erwartete Mengen je Periode und,
je nach Tiefe, die beste Altersregel, die beste Tabelle f(Gesamtbestand) und f(Gesamtbestand, älteste Klasse).

Erzeugen (die vorgerechnete Datei nennt 241 s Gesamtlaufzeit, je nach Rechner, Prozesszahl und Last):
    python vdw_grid.py --out data/vdw_grid.json --jobs 2
Die Datei liegt im Repo (unter 1 MB); die App liest sie nur. `tests/test_grid.py` rechnet die kleinen Zellen neu und vergleicht.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

import vdw_rules as R
from vdw_algorithm import Perishable, Settings, box_states

DATA_FILE = Path(__file__).resolve().parent / "data" / "vdw_grid.json"
W_VALUES = (0.0, 1.0, 3.0, 10.0, 30.0)
P_VALUES = (4.0, 9.0, 19.0)
M_MAX = {0: 7, 1: 6}                  # größte gerechnete Haltbarkeit je Lieferzeit
LIVE_M_MAX = {0: 5, 1: 4}             # bis hierher rechnet die App selbst (höchstens 1.820 Zustände)
T_MAIN, T_P = 12, 14
KEY_FIELDS = ("lead", "rule", "w", "p", "m", "T")


def depth_for(lead: int, m: int, w: float, p: float) -> int:
    """0: nur DP und Base-Stock; 1: dazu Altersregel und Tabelle f(Gesamtbestand); 2: dazu Tabelle f(Gesamtbestand, älteste Klasse)."""
    if m <= 4:
        return 2 if (w in (3.0, 10.0) and p == 9.0) else 1
    if lead == 0 and m == 5:
        return 1
    return 0


def compute_cell(lead: int, rule: str, w: float, p: float, m: int, T: int, depth: int) -> dict:
    t0 = time.time()
    cfg = Settings(m=m, lead=lead, rule=rule, w=w, p=p, T=T)
    P = Perishable(cfg)
    g, pol, h, it, cert = P.solve()
    g_dp, pi = P.evaluate(pol)
    assert abs(g - g_dp) < 1e-7, (g, g_dp)
    ae = P.eff(pol)
    supp = pi > 1e-9
    g_bs, level, pi_bs = P.best_base_stock()
    bs_pol = P.base_stock(level)
    Q = P.qvalues(h)
    qmin = Q.min(axis=1)
    sb = pi_bs > 1e-9
    qgap = (Q[np.arange(P.S), np.minimum(bs_pol, P.amax)] - qmin)[sb]
    ord_dp, stock_dp = P.edge_mass(pol, pi)
    ord_bs, stock_bs = P.edge_mass(bs_pol, pi_bs)
    comp_dp = P.components(pol, pi)
    comp_bs = P.components(bs_pol, pi_bs)
    amb_tot = R.ambiguity(P, ae, supp, lambda s: P.tot[s])
    amb_z1 = R.ambiguity(P, ae, supp, lambda s: (P.tot[s], P.z1[s]))
    cell = {
        "lead": lead, "rule": rule, "w": w, "p": p, "m": m, "T": T, "depth": depth,
        "states": P.S, "box": box_states(P.k, T), "reach_any": P.reach_any_order(), "reach_dp": int(supp.sum()), "reach_bs": int(sb.sum()),
        "g": g, "cert": cert, "iterations": it, "g_bs": g_bs, "S_bs": level, "gap_bs": 100 * (g_bs / g - 1),
        "qgap_max": float(qgap.max()), "qgap_mean": float((qgap * pi_bs[sb]).sum()),
        "edge_order_dp": ord_dp, "edge_stock_dp": stock_dp, "edge_order_bs": ord_bs, "edge_stock_bs": stock_bs,
        "amb_tot": list(amb_tot), "amb_tot_z1": list(amb_z1),
        "dp": comp_dp, "bs": comp_bs,
    }
    if depth >= 1:
        g_age, s_age, beta = R.best_age_rule(P)
        cell.update(gap_age=100 * (g_age / g - 1), age_S=s_age, age_beta=beta)
        g_wo, s_wo = R.best_without_oldest(P)
        cell.update(gap_without_oldest=100 * (g_wo / g - 1), S_without_oldest=s_wo)
        cell["gap_tab_total"] = 100 * (R.best_table_by_total(P, pol, pi, bs_pol) / g - 1)
    if depth >= 2:
        cell["gap_tab_total_z1"] = 100 * (R.best_table_by_total_and_oldest(P, bs_pol) / g - 1)
    cell["seconds"] = round(time.time() - t0, 1)
    return cell


def all_cells() -> list[tuple]:
    """Alle Zellen des Rasters als (lead, rule, w, p, m, T, depth): Hauptraster (p = 9, T = 12) und Strafverhältnis-Raster (T = 14)."""
    cells = []
    for lead in (0, 1):
        for rule in ("FIFO", "LIFO"):
            for w in W_VALUES:
                for m in range(2, M_MAX[lead] + 1):
                    cells.append((lead, rule, w, 9.0, m, T_MAIN, depth_for(lead, m, w, 9.0)))
    for p in P_VALUES:
        for lead in (0, 1):
            for rule in ("FIFO", "LIFO"):
                for w in (3.0, 10.0):
                    for m in (2, 3, 4):
                        cells.append((lead, rule, w, p, m, T_P, 1))
    return cells


def _run(args):
    return compute_cell(*args)


def generate(out: Path, jobs: int = 1, only_small: bool = False) -> dict:
    cells = all_cells()
    if only_small:
        cells = [c for c in cells if c[4] <= 3]
    cells.sort(key=lambda c: -(c[4] + 3 * c[0]))          # teure zuerst, damit die Last gleichmäßig endet
    t0 = time.time()
    if jobs > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=jobs) as ex:
            done = list(ex.map(_run, cells))
    else:
        done = [_run(c) for c in cells]
    done.sort(key=lambda c: (c["p"], c["T"], c["lead"], c["rule"], c["w"], c["m"]))
    meta = {
        "modell": "ein Artikel, feste Haltbarkeit m, Poisson-Nachfrage Mittel 3 (bei 16 gekappt), h = 1, p wie angegeben, Bestellkosten 0, "
                  "verlorene Nachfrage, Bestandsgrenze T",
        "kostenkonvention": "h nur je übertragenem Stück, w je ablaufendem Stück, p je nicht bedientem Stück",
        "zellen": len(done), "sekunden": round(time.time() - t0),
    }
    data = {"meta": meta, "cells": done}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return data


_CACHE: dict = {}


def load(path: Path | None = None) -> dict:
    """Vorgerechnetes Raster als Wörterbuch {(lead, rule, w, p, m, T): Zelle}."""
    path = path or DATA_FILE
    if path not in _CACHE:
        data = json.loads(path.read_text(encoding="utf-8"))
        _CACHE[path] = {tuple(c[k] for k in KEY_FIELDS): c for c in data["cells"]}
    return _CACHE[path]


def lookup(lead: int, rule: str, w: float, m: int, p: float = 9.0, T: int | None = None) -> dict | None:
    """Zelle des Rasters oder None, wenn sie nicht gerechnet ist."""
    T = T if T is not None else (T_MAIN if p == 9.0 else T_P)
    return load().get((lead, rule, float(w), float(p), m, T))


def is_live(lead: int, m: int) -> bool:
    """Rechnet die App diese Zelle selbst (höchstens 1.820 Zustände)?"""
    return m <= LIVE_M_MAX[lead]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(DATA_FILE))
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--small", action="store_true", help="nur Haltbarkeit 2 und 3 (zum Probieren)")
    ns = ap.parse_args()
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    res = generate(Path(ns.out), jobs=ns.jobs, only_small=ns.small)
    print(f"{res['meta']['zellen']} Zellen in {res['meta']['sekunden']} s nach {ns.out}", file=sys.stderr)
