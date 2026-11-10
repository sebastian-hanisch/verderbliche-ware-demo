"""AppTest über Inhalte: alle Reiter, jedes Preset mit der erwarteten Verdikt-Zeile, Ränder, Permalink, nicht gerechnete Zelle."""

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import vdw_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))


def _run(**params) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    for k, v in params.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _texts(at):
    return [x.value for x in list(at.success) + list(at.info) + list(at.warning) + list(at.error)]


def test_all_six_tabs_and_the_fixed_sections_exist():
    at = _run()
    assert [t.label for t in at.tabs] == ["1 · Handbeispiel", "2 · Raster", "3 · Zustandsraum", "4 · Was nutzt die exakte Politik?", "5 · Altersregel", "6 · Kostenzerlegung"]
    labels = [e.label for e in at.expander]
    assert "⚠️ Annahmen, Grenzen und bekannte Probleme" in labels and "📐 Mathematische Formulierung" in labels
    assert len(at.metric) >= 4
    assert len(at.get("graphviz_chart")) == 2                         # Zustandsgraph je Ausgaberegel im Handbeispiel
    assert len(at.get("plotly_chart")) >= 6                    # zwei Raster, Zustandsraum, Balken, Zielkarte, Altersraster, Zerlegung


EXPECTED = {
    "Handbeispiel (Haltbarkeit 2)": ("warning", "+3,80 %"),
    "FIFO, Lieferzeit 0: der Gesamtbestand reicht": ("success", "exakt optimal"),
    "LIFO: das Alter zählt": ("warning", "+6,15 %"),
    "w = h: die Ausgaberegel ist gleichgültig": ("success", "exakt optimal"),
    "Lieferzeit 1: erst der Effekt der Lieferzeit": ("warning", "+1,93 %"),
    "Haltbarkeit 5: 1.820 Zustände, 126 erreichbar": ("info", "+0,26 %"),
}


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_each_preset_shows_its_expected_headline_verdict(name):
    at = _run()
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    kind, snippet = EXPECTED[name]
    boxes = {"success": at.success, "info": at.info, "warning": at.warning}[kind]
    headline = [b.value for b in boxes if b.value.startswith("Beste Base-Stock-Regel")]
    assert headline and snippet in headline[0], (name, [b.value[:80] for b in boxes])


def test_cell_not_precomputed_gives_a_message_and_no_crash():
    at = _run(lead="1", m="7")
    assert any("nichts gerechnet" in t for t in _texts(at))
    assert not [s for s in at.slider if s.key and s.key.startswith("age_")]     # Altersregel nicht live für diese Zelle


def test_age_sliders_exist_for_live_cells_with_the_best_rule_as_default():
    at = _run(m="3", lead="0", rule="LIFO", w="10.0")
    sl = {s.key: s.value for s in at.slider if s.key and s.key.startswith("age_")}
    assert sl == {"age_s_0_LIFO_10_3": 4, "age_b_0_LIFO_10_3": -0.75}
    assert any("schließt **63 %**" in t for t in _texts(at))


def test_changing_the_age_rule_changes_its_gap():
    at = _run(m="3", lead="0", rule="LIFO", w="10.0")
    before = [m.value for m in at.metric if m.label == "Lücke der gewählten Regel"]
    at.slider(key="age_b_0_LIFO_10_3").set_value(0.0).run()
    assert not at.exception
    after = [m.value for m in at.metric if m.label == "Lücke der gewählten Regel"]
    assert before == ["+2,25 %"] and after == ["+6,15 %"]                         # beta = 0 ist der Base-Stock


def test_permalink_values_are_clamped_and_invalid_values_ignored():
    at = _run(m="99", w="5.0", rule="LILO", lead="1")
    assert at.sidebar.slider(key="m_slider").value == C.M_MAX
    assert at.sidebar.select_slider(key="w_select").value == C.DEFAULT_W              # 5 ist kein erlaubter Wert
    assert at.sidebar.radio(key="rule_radio").value == C.DEFAULT_RULE
    assert at.sidebar.radio(key="lead_radio").value == 1


def test_raster_p_and_metric_controls_run_without_error():
    at = _run()
    for p in (4.0, 19.0):
        at.radio(key="raster_p").set_value(p).run()
        assert not at.exception, [str(e) for e in at.exception]
    for metric in ("Altersregel S + β·z₁", "Tabelle a(Gesamtbestand)", "Tabelle a(Gesamtbestand, z₁)"):
        at.selectbox(key="raster_metric").set_value(metric).run()
        assert not at.exception, [str(e) for e in at.exception]


def test_every_cell_of_the_slider_grid_renders():
    """Alle Kombinationen aus Lieferzeit und Haltbarkeit am Rand (kleinste, größte live, erste nicht live, größte)."""
    for lead, m in ((0, 2), (0, 5), (0, 6), (0, 7), (1, 2), (1, 4), (1, 5), (1, 6)):
        at = _run(lead=str(lead), m=str(m), rule="LIFO", w="30.0")
        assert at.metric, (lead, m)


def test_hand_example_tab_names_the_exact_fractions():
    at = _run()
    texts = _texts(at)
    assert any("25/13" in t and "59/23" in t and "16/7" in t for t in texts)
