"""Verdikte an von Hand gesetzten Zellen (DEMO-PLAYBOOK §12): jede Schwelle und jede Zahl im Text steht hier.

Ein Verdikt ist eine reine Funktion (Art, Text) auf Zellen-Wörterbüchern; die Tests bauen die Zellen von Hand statt aus der Datei, damit Grenzen
(Lücke 0,005 %, Q-Abstand, Marke 0,5 %, Anteil 90 %) direkt geprüft werden."""

from fractions import Fraction as F

import pytest

import vdw_evaluation as ev
import vdw_hand as H


def cell(**kw):
    base = dict(lead=0, rule="LIFO", w=10.0, p=9.0, m=3, T=12, states=91, box=169, reach_any=91, reach_dp=21, reach_bs=21, g=5.6394, g_bs=5.9860, S_bs=4,
                gap_bs=6.15, qgap_max=0.3, dp={"carry": 1.0, "lost": 0.1, "waste": 0.2}, bs={"carry": 1.0, "lost": 0.1, "waste": 0.3})
    base.update(kw)
    return base


def test_formatting_uses_decimal_comma_thousands_dot_and_no_negative_zero():
    assert ev.de(3.8049, 2) == "3,80" and ev.de(3.8049, 2, True) == "+3,80" and ev.de(-0.5, 2, True) == "-0,50"
    assert ev.de(-0.00001, 2, True) == "+0,00" and ev.de(-0.00001, 2) == "0,00"
    assert ev.de_int(1820) == "1.820" and ev.de_int(18564) == "18.564" and ev.de_int(91) == "91"


def test_exact_needs_small_gap_and_zero_q_distance():
    assert ev.is_exact(cell(gap_bs=0.004, qgap_max=0.0))
    assert not ev.is_exact(cell(gap_bs=0.005, qgap_max=0.0))                 # Schwelle exklusiv
    assert not ev.is_exact(cell(gap_bs=0.0, qgap_max=1e-3))                  # Lücke null, aber die Aktion weicht ab
    assert ev.is_exact(cell(gap_bs=-1e-9, qgap_max=0.0))


def test_headline_three_branches_and_their_numbers():
    kind, text = ev.verdict_headline(cell(gap_bs=-1e-9, qgap_max=0.0, g=3.3479, g_bs=3.3479, S_bs=5, reach_bs=126))
    assert kind == "success" and "exakt optimal" in text and "Lücke 0,00 %" in text and "S = 5" in text and "126 Zuständen" in text
    kind, text = ev.verdict_headline(cell(gap_bs=0.63, qgap_max=0.1))
    assert kind == "info" and "+0,63 %" in text and "klein" in text
    kind, text = ev.verdict_headline(cell(gap_bs=6.15, gap_age=2.25, age_S=4, age_beta=-0.75))
    assert kind == "warning" and "+6,15 %" in text and "63 %" in text            # 1 - 2,25 / 6,15 = 63,4 %
    assert "5,9860" in text and "5,6394" in text
    kind, text = ev.verdict_headline(cell(gap_bs=1.0, qgap_max=0.1))              # Schwelle 1 % ist exklusiv für „klein“
    assert kind == "warning"


def test_share_closed_threshold_and_value():
    assert ev.share_closed(cell(gap_bs=6.0, gap_age=1.5)) == pytest.approx(75.0)
    assert ev.share_closed(cell(gap_bs=0.05, gap_age=0.0)) is None
    assert ev.share_closed(cell(gap_bs=4.0, gap_age=-1e-9)) == pytest.approx(100.0)
    assert ev.share_closed(cell(gap_bs=4.0)) is None                               # Altersregel nicht gerechnet


def test_raster_verdict_counts_exact_cells_and_names_exceptions():
    exact = [cell(m=m, gap_bs=0.0, qgap_max=0.0) for m in (4, 5, 6)]
    rest = [cell(m=2, w=0.0, gap_bs=1.25), cell(m=3, w=30.0, gap_bs=1.01)]
    kind, text = ev.verdict_raster(exact)
    assert kind == "success" and "3 von 3 Zellen exakt" in text
    kind, text = ev.verdict_raster(exact + rest)
    assert kind == "info" and "3 von 5 Zellen exakt" in text and "+1,25 %" in text and "Haltbarkeit 2, w = 0: +1,25 %" in text and "Haltbarkeit 3, w = 30: +1,01 %" in text
    kind, text = ev.verdict_raster(rest)
    assert kind == "warning" and "0 von 2 Zellen exakt" in text
    assert ev.verdict_raster([])[0] == "info"
    many = [cell(m=2, w=float(w), gap_bs=1.0 + w) for w in range(8)]
    assert "und 2 weitere" in ev.verdict_raster(many)[1]


def test_raster_verdict_for_tables_uses_the_half_percent_mark():
    cells = [cell(gap_tab_total=0.49), cell(gap_tab_total=0.5), cell(gap_tab_total=3.0, m=4)]
    kind, text = ev.verdict_raster(cells, "gap_tab_total", "Tabelle a(Gesamtbestand)")
    assert kind == "info" and "1 von 3 Zellen unter 0,5 %" in text and "+3,00 %" in text and "Haltbarkeit 4" in text
    assert ev.verdict_raster([cell(gap_tab_total=0.1)], "gap_tab_total")[0] == "success"
    assert ev.verdict_raster([cell(gap_tab_total=2.0)], "gap_tab_total")[0] == "warning"
    assert ev.verdict_raster([cell()], "gap_tab_total")[0] == "info"             # Maß nicht gerechnet


def test_statespace_verdict_names_all_counts():
    kind, text = ev.verdict_statespace(cell(m=5, states=1820, box=28561, reach_dp=126, reach_bs=140, reach_any=1820))
    assert kind == "info" and "1.820 Zustände" in text and "28.561" in text and "126" in text and "6,9 %" in text and "140" in text


def test_tables_verdict_branches():
    assert "nicht vorgerechnet" in ev.verdict_tables(cell())[1]
    kind, text = ev.verdict_tables(cell(gap_tab_total=0.3, gap_bs=0.63))
    assert kind == "success" and "+0,30 %" in text and "+0,63 %" in text
    kind, text = ev.verdict_tables(cell(gap_tab_total=3.0, gap_tab_total_z1=0.5, gap_bs=6.0))
    assert kind == "info" and "+0,50 %" in text and "Hälfte" in text
    kind, text = ev.verdict_tables(cell(gap_tab_total=3.0, gap_tab_total_z1=2.0, gap_bs=6.0))
    assert kind == "warning" and "+2,00 %" in text
    assert ev.verdict_tables(cell(gap_tab_total=0.5, gap_bs=2.0))[0] == "warning"      # Marke 0,5 % exklusiv


def test_age_rule_verdict_branches():
    assert ev.verdict_age_rule(None)[0] == "info"
    assert ev.verdict_age_rule(cell())[0] == "info"
    kind, text = ev.verdict_age_rule(cell(gap_bs=6.0, gap_age=0.5, age_S=4, age_beta=-0.75), 1.234)
    assert kind == "success" and "S = 4" in text and "-0,75" in text and "92 %" in text and "+1,23 %" in text   # 1 - 0,5/6 = 91,7 %
    kind, text = ev.verdict_age_rule(cell(gap_bs=6.0, gap_age=3.0, age_S=4, age_beta=-2.0))
    assert kind == "info" and "50 %" in text and "Rand des Rasters" in text
    kind, text = ev.verdict_age_rule(cell(gap_bs=0.0, gap_age=0.0, age_S=5, age_beta=0.0))
    assert kind == "info" and "nichts zu schließen" in text


def test_cost_terms_decompose_the_cost():
    t = ev.cost_terms({"carry": 1.0, "lost": 0.1, "waste": 0.2}, p=9.0, w=10.0)
    assert t["lager"] == pytest.approx(1.2) and t["fehl"] == pytest.approx(0.9) and t["verfall"] == pytest.approx(1.8)
    assert t["summe"] == pytest.approx(1.0 + 9.0 * 0.1 + 10.0 * 0.2)               # h carry + p lost + w waste
    assert ev.cost_terms({"carry": 1.0, "lost": 0.0, "waste": 0.5}, p=9.0, w=0.0)["verfall"] == pytest.approx(-0.5)


def test_decomposition_verdict_branches():
    f = cell(rule="FIFO", g=3.3479, w=1.0, lead=0, bs={"carry": 1, "lost": 0, "waste": 0.0009})
    l = cell(rule="LIFO", g=3.3479, w=1.0, lead=0, bs={"carry": 1, "lost": 0, "waste": 0.174})
    kind, text = ev.verdict_decomposition(f, l)
    assert kind == "success" and "gleich" in text and "FIFO 0,0009" in text and "LIFO 0,1740" in text and "Bestand nach der Bestellung" in text
    kind, text = ev.verdict_decomposition(cell(rule="FIFO", g=2.0, w=3.0), cell(rule="LIFO", g=2.4, w=3.0))
    assert kind == "warning" and "20,0 %" in text and "über" in text
    kind, text = ev.verdict_decomposition(cell(rule="FIFO", g=2.0, w=1.0, lead=1), cell(rule="LIFO", g=1.96, w=1.0, lead=1))
    assert kind == "warning" and "2,0 %" in text and "unter" in text
    kind, text = ev.verdict_decomposition(cell(rule="FIFO", g=2.0, w=0.0), cell(rule="LIFO", g=1.5, w=0.0))
    assert kind == "info" and "25,0 % billiger" in text and "Kostenkonvention" in text


def test_hand_verdict_names_fractions_and_the_gap():
    kind, text = ev.verdict_hand(H.summary("FIFO"), H.summary("LIFO"))
    assert kind == "info" and "25/13" in text and "16/7" in text and "59/23" in text and "+12,23 %" in text and "(2, 1, 0)" in text and "(2, 0, 0)" in text
    assert F(59, 23) / F(16, 7) - 1 > F(12, 100)
