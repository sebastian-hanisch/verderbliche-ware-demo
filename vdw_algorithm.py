"""Kern: Bestandsmodell mit fester Haltbarkeit (Zustand = Bestand je Restlebensdauer), exakte Rechnung.

Modell: ein Artikel, feste Haltbarkeit m Perioden, verlorene Nachfrage, Lieferzeit 0 oder 1, Ausgaberegel FIFO oder LIFO.
Zustand z = (z_1, ..., z_k): Stück mit noch 1, ..., k Perioden Restlebensdauer (Spalte 0 = älteste Klasse). Bei Lieferzeit 0 ist k = m - 1
(die Bestellung kommt mit Restlebensdauer m an und wird in derselben Periode verkauft), bei Lieferzeit 1 ist k = m (die Bestellung steht in der
nächsten Periode als Klasse m im Bestand). Es werden nur Zustände mit Summe höchstens T aufgezählt: Zahl der Zustände C(T + k, k)
(statt des Kastens (T + 1)^k).

Zeitfolge je Periode. Lieferzeit 0: Bestellung a kommt frisch an, dann die Nachfrage d. Lieferzeit 1: die Nachfrage trifft den Bestand,
die Bestellung kommt vor der nächsten Periode frisch an. Kosten je Periode (Kostenkonvention): h je am Periodenende **übertragenes**
Stück, p je nicht bediente Nachfrage, w je am Periodenende ablaufendes Stück. Ablaufende Stücke kosten also kein h. Bei w = 0 ist LIFO
deshalb billiger als FIFO (ablaufende Ware kostet nichts), das ist eine Folge dieser Konvention.

Bestandsgrenze T: Lieferzeit 0: Bestand nach der Bestellung höchstens T; Lieferzeit 1: Bestand der nächsten Periode höchstens T.
Eine größere Bestellung wird auf das Zulässige gekappt.

Rechenweg: relative Wertiteration auf der trägen Kette P' = tau P + (1 - tau) I (gegen Periodizität, siehe `Perishable.solve`), exakte
Auswertung fester Politiken über die stationäre Verteilung der von leer erreichbaren Zustände. Kein Zufall im Kern.
"""

from __future__ import annotations

import dataclasses
from math import comb, exp, factorial

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.sparse.csgraph import breadth_first_order

RULES = ("FIFO", "LIFO")


@dataclasses.dataclass(frozen=True, kw_only=True)
class Settings:
    """Einstellungen des Modells; nur mit Schlüsselwörtern (ein eingefügtes Feld darf nie still Werte verschieben)."""

    m: int = 2                # Haltbarkeit in Perioden (ein Stück mit Restlebensdauer 1 läuft am Periodenende ab)
    lead: int = 0             # Lieferzeit 0 oder 1
    rule: str = "FIFO"        # Ausgaberegel: FIFO (ältestes zuerst) oder LIFO (frischestes zuerst)
    mean: float = 3.0         # Mittel der Poisson-Nachfrage
    h: float = 1.0            # Kosten je übertragenem Stück
    p: float = 9.0            # Kosten je nicht bedientem Stück
    w: float = 3.0            # Kosten je ablaufendem Stück
    T: int = 12               # Bestandsgrenze
    dmax: int = 16            # Nachfrage wird bei dmax gekappt (Rest der Wahrscheinlichkeit auf dmax)
    demand: tuple = ()        # wenn gesetzt: Wahrscheinlichkeiten der Nachfrage 0, 1, ... statt Poisson

    def __post_init__(self):
        if self.m < 2:
            raise ValueError("Haltbarkeit m >= 2")
        if self.lead not in (0, 1):
            raise ValueError("Lieferzeit 0 oder 1")
        if self.rule not in RULES:
            raise ValueError("Ausgaberegel FIFO oder LIFO")
        if self.T < 1:
            raise ValueError("Bestandsgrenze T >= 1")

    @property
    def k(self) -> int:
        """Zahl der Altersklassen im Zustand."""
        return self.m - 1 if self.lead == 0 else self.m


def poisson_pmf(mean: float, dmax: int) -> np.ndarray:
    """Poisson(mean) auf 0..dmax, der Rest der Wahrscheinlichkeit liegt auf dmax."""
    p = np.array([exp(-mean) * mean**j / factorial(j) for j in range(dmax + 1)])
    p[-1] += 1.0 - p.sum()
    return p


def n_states(k: int, T: int) -> int:
    """Zahl der Zustände mit k Altersklassen und Gesamtbestand höchstens T: C(T + k, k)."""
    return comb(T + k, k)


def box_states(k: int, T: int) -> int:
    """Kasten (T + 1)^k: so viele Zustände hätte die Aufzählung ohne Gesamtgrenze."""
    return (T + 1) ** k


def compositions(k: int, T: int) -> np.ndarray:
    """Alle Vektoren (z_1, ..., z_k) mit z_i >= 0 und Summe höchstens T; Zeilenindex = Zustand."""
    out: list[list[int]] = []

    def rec(prefix, left, i):
        if i == k:
            out.append(prefix)
            return
        for v in range(left + 1):
            rec(prefix + [v], left - v, i + 1)

    rec([], T, 0)
    return np.array(out, dtype=np.int64).reshape(len(out), k)


def issue(units: np.ndarray, d, rule: str) -> np.ndarray:
    """Ausgabe der Nachfrage d aus dem Bestand `units` (Zeile 0 = älteste Klasse, Spalten = Zustände). Rückgabe: Restbestand je Klasse.

    FIFO nimmt die älteste Klasse zuerst, LIFO die frischeste."""
    if rule == "FIFO":
        cum = np.cumsum(units, axis=0)
        return np.clip(cum - d, 0, units)
    rev = units[::-1]
    cum = np.cumsum(rev, axis=0)
    return np.clip(cum - d, 0, rev)[::-1]


def step_cost_terms(units: np.ndarray, d, rule: str):
    """Eine Periode auf einem Bestandsvektor: (Rest je Klasse, nicht bediente Menge, ablaufende Menge, übertragene Menge)."""
    rem = issue(units, d, rule)
    lost = np.maximum(d - units.sum(axis=0), 0)
    return rem, lost, rem[0], rem[1:].sum(axis=0)


class Perishable:
    """Zustandsraum, Übergänge und Kosten für alle Zustände und Bestellmengen 0..T."""

    def __init__(self, cfg: Settings):
        self.cfg = cfg
        T, k = cfg.T, cfg.k
        self.k = k
        self.Z = compositions(k, T)               # (S, k), Spalte 0 = älteste Klasse
        self.S = len(self.Z)
        assert self.S == n_states(k, T)
        self.tot = self.Z.sum(axis=1)
        self.z1 = self.Z[:, 0]
        self._mult = (T + 1) ** np.arange(k - 1, -1, -1, dtype=np.int64)
        keys = self.Z @ self._mult
        self._order = np.argsort(keys)
        self._skeys = keys[self._order]
        self.empty = int(np.flatnonzero(self.tot == 0)[0])
        if cfg.demand:
            pd = np.array(cfg.demand, dtype=float)
            self.pd = pd / pd.sum()
        else:
            self.pd = poisson_pmf(cfg.mean, cfg.dmax)
        self.d = np.arange(len(self.pd))
        # größte zulässige Bestellung je Zustand
        self.amax = T - self.tot if cfg.lead == 0 else T - (self.tot - self.z1)
        self.A = T + 1
        self._build()

    # ------------------------------------------------------------------ Aufbau
    def index(self, Zn: np.ndarray) -> np.ndarray:
        """Zeilenindex für eine Matrix (S, k) von Zustandsvektoren."""
        keys = Zn @ self._mult
        pos = np.searchsorted(self._skeys, keys)
        assert np.all(self._skeys[pos] == keys), "Zustand außerhalb des Raums"
        return self._order[pos]

    def _build(self):
        c, S = self.cfg, self.S
        Zt = self.Z.T                              # (k, S)
        self.P = []
        self.ecarry = np.zeros((S, self.A))        # erwartete übertragene Menge
        self.elost = np.zeros((S, self.A))         # erwartete nicht bediente Menge
        self.ewaste = np.zeros((S, self.A))        # erwartete ablaufende Menge
        for a in range(self.A):
            ae = np.minimum(a, self.amax)
            units = np.vstack([Zt, ae[None, :]]) if c.lead == 0 else Zt
            rows, cols, vals = [], [], []
            for dd, pr in zip(self.d, self.pd):
                rem, lost, waste, carry = step_cost_terms(units, dd, c.rule)
                self.ecarry[:, a] += pr * carry
                self.elost[:, a] += pr * lost
                self.ewaste[:, a] += pr * waste
                zn = rem[1:] if c.lead == 0 else np.vstack([rem[1:], ae[None, :]])
                rows.append(np.arange(S))
                cols.append(self.index(zn.T.copy()))
                vals.append(np.full(S, pr))
            self.P.append(sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(S, S)))
        self._Pall = sp.vstack(self.P, format="csr")
        self.cost = c.h * self.ecarry + c.p * self.elost + c.w * self.ewaste  # (S, A): h mal übertragen + p mal nicht bedient + w mal ablaufend

    # ------------------------------------------------------------------ Politiken
    def eff(self, pol: np.ndarray) -> np.ndarray:
        """Tatsächliche Bestellmenge (auf das Zulässige gekappt)."""
        return np.minimum(pol, self.amax)

    def base_stock(self, level: int) -> np.ndarray:
        """Auffüllen auf `level`, gemessen am Gesamtbestand."""
        return np.clip(level - self.tot, 0, None).astype(int)

    def position_rule(self, level, position: np.ndarray) -> np.ndarray:
        """Auffüllen auf `level`, gemessen an einer beliebigen Position je Zustand (Vektor oder Zielvektor)."""
        return np.clip(np.asarray(level) - position, 0, None).astype(int)

    def chain(self, pol: np.ndarray):
        """Übergangsmatrix und erwartete Kosten je Zustand unter der Politik."""
        idx = pol.astype(np.int64) * self.S + np.arange(self.S)
        return self._Pall[idx], self.cost[np.arange(self.S), pol]

    # ------------------------------------------------------------------ exakte Auswertung
    def reachable(self, pol: np.ndarray) -> np.ndarray:
        Pp, _ = self.chain(pol)
        return np.sort(breadth_first_order(Pp, self.empty, directed=True, return_predecessors=False))

    def stationary(self, pol: np.ndarray) -> np.ndarray:
        """Stationäre Verteilung der von leer erreichbaren Zustände (null außerhalb)."""
        Pp, _ = self.chain(pol)
        R = self.reachable(pol)
        n = len(R)
        PR = Pp[R][:, R].tocsr()
        At = (sp.identity(n, format="csr") - PR).T.tocsr()
        M = sp.vstack([At[:-1], sp.csr_matrix(np.ones((1, n)))], format="csc")
        rhs = np.zeros(n)
        rhs[-1] = 1.0
        pi = np.zeros(self.S)
        pi[R] = spla.spsolve(M, rhs)
        return pi

    def evaluate(self, pol: np.ndarray):
        """Kosten je Periode der festen Politik und stationäre Verteilung."""
        pi = self.stationary(pol)
        _, cp = self.chain(pol)
        return float(pi @ cp), pi

    def components(self, pol: np.ndarray, pi: np.ndarray | None = None) -> dict:
        """Erwartete Mengen je Periode unter der Politik: übertragen, nicht bedient, ablaufend (Kosten = h*übertragen + p*nicht bedient + w*ablaufend)."""
        if pi is None:
            pi = self.stationary(pol)
        ar = np.arange(self.S)
        carry = float(pi @ self.ecarry[ar, pol])
        lost = float(pi @ self.elost[ar, pol])
        waste = float(pi @ self.ewaste[ar, pol])
        return {"carry": carry, "lost": lost, "waste": waste}

    # ------------------------------------------------------------------ exakte Optimierung
    def _q(self, h: np.ndarray, tau: float) -> np.ndarray:
        cost = self.cost
        Q = np.empty((self.S, self.A))
        for a in range(self.A):
            Q[:, a] = tau * (cost[:, a] + self.P[a] @ h) + (1 - tau) * h
        return Q

    def solve(self, tol: float = 1e-10, tau: float = 0.5, maxit: int = 200000):
        """Relative Wertiteration mit Aperiodizitäts-Transformation (träge Kette P' = tau P + (1 - tau) I, Kosten tau c; gleiche optimale
        Politik, Gewinn g' = tau g). Ohne sie schwingt die Iteration bei periodischen Ketten (Lieferzeit 1, LIFO, Haltbarkeit 2: keine
        Konvergenz in 99.999 Iterationen). Rückgabe: Kosten g je Periode, Politik, Wertefunktion, Iterationen und Zertifikat (Spannweite der
        Bellman-Differenz, geteilt durch tau; g liegt in ihr)."""
        h = np.zeros(self.S)
        ref = self.empty
        span = np.inf
        d = np.zeros(self.S)
        it = 0
        for it in range(maxit):
            v = self._q(h, tau).min(axis=1)
            d = v - h
            span = float(d.max() - d.min())
            h = v - v[ref]
            if span < tol * tau:
                break
        g = 0.5 * float(d.max() + d.min()) / tau
        pol = self._q(h, tau).argmin(axis=1)
        return g, pol, h, it, span / tau

    def qvalues(self, h: np.ndarray) -> np.ndarray:
        """Q(Zustand, Bestellung) = Periodenkosten + Erwartung der Wertefunktion h des Folgezustands (ohne träge Kette)."""
        cost = self.cost
        Q = np.empty((self.S, self.A))
        for a in range(self.A):
            Q[:, a] = cost[:, a] + self.P[a] @ h
        return Q

    def best_base_stock(self):
        """Bester Base-Stock auf dem Gesamtbestand: (Kosten, S, stationäre Verteilung). Durchlauf von klein nach groß, Abbruch nach drei
        Verschlechterungen in Folge (die Kosten sind in S unimodal; die Gegenprobe über alle S steht in tests/test_oracle_*.py)."""
        best = (np.inf, None, None)
        worse = 0
        for level in range(0, self.cfg.T + 1):
            g, pi = self.evaluate(self.base_stock(level))
            if g < best[0] - 1e-12:
                best = (g, level, pi)
                worse = 0
            else:
                worse += 1
                if worse >= 3:
                    break
        return best

    def reach_any_order(self) -> int:
        """Zahl der von leer erreichbaren Zustände bei beliebiger Bestellmenge (Vereinigung aller Aktionen)."""
        U = sum(self.P).tocsr()
        return len(breadth_first_order(U, self.empty, directed=True, return_predecessors=False))

    def edge_mass(self, pol: np.ndarray, pi: np.ndarray):
        """(Anteil der Zeit, in dem die Bestellung an der Bestandsgrenze hängt, Anteil der Zeit mit Bestand am Rand T)."""
        ae = self.eff(pol)
        at_order = float(pi[(ae == self.amax) & (ae > 0)].sum())
        at_stock = float(pi[self.tot >= self.cfg.T].sum())
        return at_order, at_stock
