"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen, jedes Preset zeigt auf eine vorgerechnete Zelle."""

import vdw_constants as C
import vdw_grid as G
import vdw_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_regler_choices_and_bounds():
    for name, preset in C.PRESETS.items():
        assert C.M_MIN <= preset["m"] <= C.M_MAX, name
        assert preset["lead"] in C.LEAD_CHOICES and preset["rule"] in C.RULE_CHOICES and preset["w"] in C.W_CHOICES, name


def test_default_preset_equals_the_default_settings():
    first = next(iter(C.PRESETS.values()))
    assert first == {"m": C.DEFAULT_M, "lead": C.DEFAULT_LEAD, "rule": C.DEFAULT_RULE, "w": C.DEFAULT_W}


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_every_preset_points_to_a_precomputed_cell_and_the_live_range_is_documented():
    for name, p in C.PRESETS.items():
        cell = G.lookup(p["lead"], p["rule"], p["w"], p["m"])
        assert cell is not None, name
        assert G.is_live(p["lead"], p["m"]), name                 # alle Presets lassen sich auch live nachrechnen


def test_preset_names_state_what_the_cell_shows():
    """Beschriftungen gegen die gemessenen Zellen (Textfalle: vertauschte Preset-Namen)."""
    cells = {name: G.lookup(p["lead"], p["rule"], p["w"], p["m"]) for name, p in C.PRESETS.items()}
    assert cells["FIFO, Lieferzeit 0: der Gesamtbestand reicht"]["gap_bs"] < 0.005
    assert cells["LIFO: das Alter zählt"]["gap_bs"] > 1.0
    assert cells["Haltbarkeit 5: 1.820 Zustände, 126 erreichbar"]["states"] == 1820
    assert cells["Haltbarkeit 5: 1.820 Zustände, 126 erreichbar"]["reach_dp"] == 126
    w_h = G.lookup(0, "FIFO", 1.0, 4)["g"], cells["w = h: die Ausgaberegel ist gleichgültig"]["g"]
    assert abs(w_h[0] - w_h[1]) < 1e-8
    assert cells["Lieferzeit 1: erst der Effekt der Lieferzeit"]["lead"] == 1
