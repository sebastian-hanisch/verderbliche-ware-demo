"""Konstanten: Regler-Grenzen, feste Annahmen, Farben, Presets und der Annahmen-Text."""

# --- Modell (feste Annahmen des Vehikels) -------------------------------------------------------------------------------------------------
MEAN_DEMAND = 3.0          # Poisson-Nachfrage, Mittel je Periode
H_COST = 1.0               # Kosten je übertragenem Stück
P_COST = 9.0               # Strafkosten je nicht bedientem Stück (Standard; 4 und 19 nur vorgerechnet)
T_LIMIT = 12               # Bestandsgrenze des Hauptrasters
T_LIMIT_P = 14             # Bestandsgrenze des Strafverhältnis-Rasters
DMAX = 16                  # Nachfrage wird bei 16 gekappt

# --- Regler ---------------------------------------------------------------------------------------------------------------------------------
M_MIN, M_MAX, DEFAULT_M = 2, 7, 2
LEAD_CHOICES = (0, 1)
RULE_CHOICES = ("FIFO", "LIFO")
W_CHOICES = (0.0, 1.0, 3.0, 10.0, 30.0)
P_CHOICES = (4.0, 9.0, 19.0)
DEFAULT_LEAD, DEFAULT_RULE, DEFAULT_W = 0, "LIFO", 3.0
LIVE_M_MAX = {0: 5, 1: 4}  # bis zu dieser Haltbarkeit rechnet die App selbst (höchstens 1.820 Zustände), darüber liest sie die vorgerechnete Datei
GRID_M_MAX = {0: 7, 1: 6}  # größte vorgerechnete Haltbarkeit je Lieferzeit

LEAD_LABELS = {0: "0 (Bestellung kommt sofort)", 1: "1 (Bestellung kommt eine Periode später)"}
RULE_LABELS = {"FIFO": "FIFO (ältestes zuerst)", "LIFO": "LIFO (frischestes zuerst)"}

# --- Farben ----------------------------------------------------------------------------------------------------------------------------------
COLOR_FIFO = "#4c78a8"
COLOR_LIFO = "#e45756"
COLOR_DP = "#2F6B65"
COLOR_BS = "#9aa0a6"
COLOR_RULE = "#f58518"
COLOR_TAB = "#72b7b2"
COLOR_TAB_Z1 = "#b279a2"
COLOR_H = "#4c78a8"
COLOR_P = "#e45756"
COLOR_W = "#f2a93b"

# --- Presets (das erste ist der Standard) ------------------------------------------------------------------------------------------------------
PRESETS = {
    "Handbeispiel (Haltbarkeit 2)": {"m": 2, "lead": 0, "rule": "LIFO", "w": 3.0},
    "FIFO, Lieferzeit 0: der Gesamtbestand reicht": {"m": 4, "lead": 0, "rule": "FIFO", "w": 10.0},
    "LIFO: das Alter zählt": {"m": 3, "lead": 0, "rule": "LIFO", "w": 10.0},
    "w = h: die Ausgaberegel ist gleichgültig": {"m": 4, "lead": 0, "rule": "LIFO", "w": 1.0},
    "Lieferzeit 1: erst der Effekt der Lieferzeit": {"m": 4, "lead": 1, "rule": "FIFO", "w": 3.0},
    "Haltbarkeit 5: 1.820 Zustände, 126 erreichbar": {"m": 5, "lead": 0, "rule": "LIFO", "w": 3.0},
}
PRESET_HELP = {
    "Handbeispiel (Haltbarkeit 2)": "Kleinster Fall: Haltbarkeit 2, Lieferzeit 0, LIFO, w = 3 (13 Zustände). Das Handbeispiel im ersten Reiter hat feste Werte (Mittel 1, w = 5) und hängt nicht von der Seitenleiste ab.",
    "FIFO, Lieferzeit 0: der Gesamtbestand reicht": "Haltbarkeit 4, Lieferzeit 0, FIFO, w = 10: der beste Base-Stock auf dem Gesamtbestand ist exakt optimal.",
    "LIFO: das Alter zählt": "Haltbarkeit 3, Lieferzeit 0, LIFO, w = 10: der Base-Stock liegt über der exakten Lösung, die Menge der ältesten Klasse hilft.",
    "w = h: die Ausgaberegel ist gleichgültig": "Haltbarkeit 4, Lieferzeit 0, LIFO, w = 1 = h: FIFO und LIFO kosten exakt dasselbe.",
    "Lieferzeit 1: erst der Effekt der Lieferzeit": "Haltbarkeit 4, Lieferzeit 1, FIFO, w = 3: die Lücke des Base-Stock ist in dieser Zelle überwiegend ein Effekt der Lieferzeit, nicht des Alters (bei Haltbarkeit 2 liegt sie deutlich darüber).",
    "Haltbarkeit 5: 1.820 Zustände, 126 erreichbar": "Haltbarkeit 5, Lieferzeit 0, LIFO, w = 3: 1.820 Zustände, unter der exakten Politik werden nur 126 erreicht.",
}

# --- Texte, die App und README gleichlautend führen (tests/test_claims.py vergleicht) ------------------------------------------------------------
ASSUMPTIONS_MARKDOWN = """\
- **Modell.** Ein Artikel, Poisson-Nachfrage mit Mittel 3 je Periode (bei 16 gekappt, Wahrscheinlichkeit darüber 2,2e-8), h = 1 je übertragenem Stück, p = 9 je nicht bedientem Stück (4 und 19 nur vorgerechnet), keine Bestellkosten, verlorene Nachfrage, feste Haltbarkeit, Bestandsgrenze 12. Alle Zahlen gelten nur für diese Voraussetzungen.
- **Kostenkonvention.** h fällt nur auf **übertragene** Stücke, w auf ablaufende. Bei w = 0 ist LIFO deshalb billiger als FIFO (ablaufende Ware kostet nichts): eine Folge der Konvention, keine Aussage über Frischware. Schlagzeilen gelten für w ≥ 1.
- **Ausgaberegel fest.** FIFO und LIFO sind vorgegebene Regeln, nicht Teil der Optimierung. Ein gemeinsames Optimum über Ausgabe- und Bestellregel ist nicht gerechnet. LIFO steht als Modell für „die Kundschaft greift nach hinten“; das ist eine Deutung, nicht gemessen.
- **Bestandsgrenze 12.** Die exakte Politik berührt sie in keiner der 110 Zellen (Randmasse 0). Einzige Auffälligkeit: Lieferzeit 1, LIFO, Haltbarkeit 2, w = 0, dort stößt der beste Base-Stock (S = 12) an die Grenze; das Ergebnis ist mit Grenze 16 und 20 identisch.
- **Tabellen nach Alter sind obere Schranken.** Die besten Tabellen a(Gesamtbestand) und a(Gesamtbestand, älteste Klasse) stammen aus einer lokalen Suche (Koordinatenabstieg), nicht aus einem Beweis. „Die DP braucht genau die älteste Klasse“ ist daraus nicht abzuleiten.
- **Altersregel.** Das Raster der Regel „Auffüllen auf S + β·z₁“ reicht von β = −2 bis +1 in Vierteln; bei Lieferzeit 0, LIFO, w = 30 und Haltbarkeit 3 bis 5 liegt das beste β am Rand (−2). In den 15 Zellen mit Haltbarkeit 3 bis 5 (Lieferzeit 0) bzw. 3 und 4 (Lieferzeit 1) schließt sie 13 bis 98 % der Lücke (Rest +0,02 bis +7,21 %); bei Haltbarkeit 2 und Lieferzeit 0 schließt sie die Lücke bei LIFO und w = 3, 10, 30 vollständig.
- **Lieferzeit 1.** Bei FIFO ist die Lücke ab Haltbarkeit 4 überwiegend der Effekt der Lieferzeit mit verlorener Nachfrage (ohne Verfall +1,75 % im selben Modell), nicht des Alters; bei Haltbarkeit 2 (und 3 mit w = 30) liegt sie deutlich darüber (bis +9,18 %). Das ist ein Vergleich mit dem Modell ohne Verfall, keine Messung der Ursache.
- **Rechenlast.** Bis Haltbarkeit 5 (Lieferzeit 0) bzw. 4 (Lieferzeit 1) rechnet die App DP, Base-Stock und Altersregel selbst. Alles Größere, die Tabellen und das Strafverhältnis-Raster sind vorgerechnet (Datei `data/vdw_grid.json`, Erzeugung mit `vdw_grid.py`).
- **Literatur.** Zustand nach Restlebensdauer und die Aussage, dass bei Lieferzeit 0 unter Base-Stock-Politiken FIFO-Ausgabe die Ablaufmenge minimiert (und bei Verfallskosten w ≥ h kostenoptimal ist), nach der arXiv-Vorfassung von Zhang, Ayer und White (2016, Volltext gelesen; die Zeitschriftenfassung nicht). Das dort zitierte Original von Chazan und Gal (1977) ist nicht gelesen. Der Abstand des Base-Stock zum Optimum je Ausgaberegel ist Messung dieser Demo, keine Literaturaussage.
"""
