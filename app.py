"""Verderbliche Ware: Zustand = Alter - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Bestandsmodell mit fester Haltbarkeit: Reicht der Gesamtbestand als Zustand, oder muss die Bestellregel das Alter der Ware kennen?
Exakte Rechnung (relative Wertiteration) gegen einfache Regeln; kleine Zellen rechnet die App selbst, größere sind vorgerechnet (data/vdw_grid.json).

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import vdw_constants as C
import vdw_evaluation as ev
import vdw_grid as G
import vdw_hand as H
import vdw_rules as R
from vdw_evaluation import de, de_int
from vdw_layout import dunkles_design, kopf_css
from vdw_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    sidebar_presets,
    sync_query_params,
)
from vdw_visualization import (
    build_age_grid,
    build_decomposition,
    build_gap_bars,
    build_raster,
    build_statespace,
    build_targets,
)

st.set_page_config(page_title="Verderbliche Ware – Sebastian Hanisch", layout="wide")


@st.cache_resource(show_spinner=False, max_entries=6)
def _live(lead, rule, w, m):
    return ev.solve_live(lead, rule, w, m)


@st.cache_data(show_spinner=False, max_entries=12)
def _age_grid(lead, rule, w, m):
    return ev.age_grid(_live(lead, rule, w, m))


@st.cache_data(show_spinner=False, max_entries=12)
def _targets(lead, rule, w, m):
    live = _live(lead, rule, w, m)
    return R.target_table(live.P, live.pol, live.pi)


@st.cache_data(show_spinner=False)
def _hand(rule):
    return H.summary(rule)


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in vdw_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🥛 Verderbliche Ware: Zustand = Alter")
st.markdown(
    """
Frische Ware läuft nach **m Perioden** ab. Muss die Bestellregel dafür wissen, **wie alt** der Bestand ist, oder reicht der **Gesamtbestand**? Die Demo rechnet die beste Bestellpolitik **exakt**
(dynamische Optimierung über alle Altersverteilungen) und misst, wie weit der einfache Base-Stock auf dem Gesamtbestand davon entfernt liegt, je nach **Ausgaberegel** (FIFO: ältestes zuerst, LIFO: frischestes zuerst),
**Lieferzeit** und **Verfallskosten**. Es ist die Demo der Reihe „Bestandspolitiken“, bei der der Zustand das Alter der Ware ist.

Weiter unten: sechs Reiter (Handbeispiel in Brüchen, Raster, Zustandsraum, „Was nutzt die exakte Politik?“, Altersregel, Kostenzerlegung), der Ausklapper **⚠️ Annahmen, Grenzen und bekannte Probleme** und der Expander **📐 Mathematische Formulierung**.
"""
)

# erklaerseite:einfach:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/verderbliche-ware-erklaert.json, nicht von Hand ändern)
with st.expander("💬 In einfachen Worten"):
    st.markdown(
        """
Verderbliche Ware hat eine feste **Haltbarkeit**. Zum Zustand des Lagers gehört dann nicht nur, wie viel da ist, sondern auch, wie alt die Ware ist. Die Demo fragt, ob die Bestellregel dieses **Alter** kennen muss. Sie rechnet die beste Regel exakt aus und vergleicht sie mit einfachen Regeln, etwa „auf einen festen Gesamtbestand auffüllen“ (**Base-Stock**) und einer **Altersregel**, die zusätzlich die älteste Ware berücksichtigt. Das Ergebnis hängt stark davon ab, welche Ware zuerst ausgegeben wird: die älteste (**FIFO**) oder die frischeste (**LIFO**). Das gilt für die gerechneten Fälle im Modell der Demo (zufällige Nachfrage, erzeugte Kosten, verlorene Nachfrage), nicht für echte Lager.

[Ausführlich und verständlich erklärt, mit Fachteil](https://sebastianhanisch.net/verderbliche-ware-erklaert.html)
        """
    )
# erklaerseite:einfach:end

with st.expander("So funktioniert die Altersführung", expanded=True):
    st.markdown(
        """
1. **Zustand = Bestand je Restlebensdauer.** Ein Stück mit Restlebensdauer 1 läuft am Ende der Periode ab. Bei Haltbarkeit m und Lieferzeit 0 gibt es m − 1 Altersklassen im Zustand (die frische Bestellung kommt erst in der Periode an), bei Lieferzeit 1 sind es m.
2. **Die Ausgaberegel entscheidet, welche Klasse verkauft wird.** FIFO verkauft die älteste Klasse zuerst, LIFO die frischeste. Ablaufende Stücke kosten w, übertragene Stücke h, fehlende p.
3. **Die exakte Politik** (dynamische Optimierung) wählt zu jedem Zustand die beste Bestellmenge. Der **Base-Stock** füllt nur den **Gesamtbestand** auf ein Niveau S auf, ohne das Alter zu kennen. Die **Lücke** ist der Mehrpreis des besten Base-Stock in Prozent der exakten Kosten.
4. **Die Zustandszahl wächst schnell:** C(T + k, k) Zustände bei Gesamtgrenze T und k Altersklassen, aber nur ein Teil wird unter der exakten Politik je erreicht (bei Lieferzeit 0 und w = 3: 6 von 13 Zuständen bei Haltbarkeit 2, 462 von 18.564 bei Haltbarkeit 7).

| Begriff | Bedeutung |
|---|---|
| Restlebensdauer | Perioden, die ein Stück noch verkauft werden kann; z₁ = Menge der ältesten Klasse (Restlebensdauer 1) |
| Base-Stock (S) | Bestellung = S minus Gesamtbestand, nie negativ |
| Q-Abstand | Kostenunterschied zwischen der Bestellung des Base-Stock und der besten Bestellung im selben Zustand; 0 heißt: dieselbe Bestellung ist auch exakt optimal |
| Lücke | Kosten der Regel geteilt durch Kosten der exakten Politik, minus 1, in Prozent |
| Zertifikat | Spannweite der Bellman-Differenz: der Kostenwert der Rechnung liegt höchstens so weit neben dem exakten |
        """
    )

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Ware**")
    m = st.slider("Haltbarkeit m (Perioden)", *bounds("m_slider"), key="m_slider",
                  help="Nach so vielen Perioden läuft ein Stück ab. Bei Lieferzeit 1 ist nur bis 6 vorgerechnet.")
    st.markdown("**Lager und Lieferung**")
    lead = st.radio("Lieferzeit (Perioden)", C.LEAD_CHOICES, key="lead_radio", format_func=lambda v: C.LEAD_LABELS[v],
                    help="Bei 0 steht die Bestellung noch in derselben Periode zur Verfügung, bei 1 erst in der nächsten.")
    rule = st.radio("Ausgaberegel", C.RULE_CHOICES, key="rule_radio", format_func=lambda v: C.RULE_LABELS[v],
                    help="Welche Altersklasse die Nachfrage zuerst bedient. Keine Optimierung: die Regel ist vorgegeben.")
    w = st.select_slider("Verfallskosten w je ablaufendem Stück", options=C.W_CHOICES, key="w_select", format_func=lambda v: de(v, 0),
                         help="h = 1 je übertragenem Stück, p = 9 je fehlendem Stück. w = h = 1 ist der Sonderfall, in dem das Alter bei Lieferzeit 0 nichts kostet; w = 0 ist ein Randfall der Kostenkonvention.")
    st.caption("Fest: Poisson-Nachfrage mit Mittel 3, h = 1, p = 9, keine Bestellkosten, verlorene Nachfrage, Bestandsgrenze 12.")

sync_query_params({"m_slider": int(m), "lead_radio": int(lead), "rule_radio": str(rule), "w_select": float(w)})

cell = G.lookup(int(lead), rule, w, int(m))
live_ok = G.is_live(int(lead), int(m))

# --- Ergebnis ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ergebnis")
if cell is None:
    st.info(f"Für Lieferzeit {lead} und Haltbarkeit {m} ist nichts gerechnet: Bei Lieferzeit 1 reicht das vorgerechnete Raster bis Haltbarkeit {C.GRID_M_MAX[1]}. "
            "Die Reiter „Raster“ und „Zustandsraum“ zeigen, was für diese Lieferzeit vorliegt.")
else:
    m1, m2, m3, m4 = st.columns(4)
    # Delta immer als „mein Wert minus Referenz“; die Farbe regelt delta_color="inverse" (Vorzeichen-Falle, DEMO-PLAYBOOK §2).
    m1.metric("Kosten der exakten Politik", de(cell["g"], 4), delta="Referenz", delta_color="off", help="Erwartete Kosten je Periode im stationären Betrieb.")
    m2.metric(f"Kosten bester Base-Stock (S = {cell['S_bs']})", de(cell["g_bs"], 4), delta=de(cell["g_bs"] - cell["g"], 4, True) + " gegen exakt", delta_color="inverse")
    m3.metric("Lücke des Base-Stock", de(max(cell["gap_bs"], 0.0), 2, True) + " %", delta="in % der exakten Kosten", delta_color="off")
    m4.metric("Zustände / davon erreicht (exakt)", f"{de_int(cell['states'])} / {de_int(cell['reach_dp'])}", delta=f"Kasten: {de_int(cell['box'])}", delta_color="off")
    st.caption(("Rechenstand: vorgerechnet (Datei data/vdw_grid.json); die Reiter 4 und 5 rechnen diese Zelle zusätzlich selbst nach." if live_ok else
                "Rechenstand: vorgerechnet (Datei data/vdw_grid.json); diese Zelle ist für die Live-Rechnung der App zu groß (mehr als 1.820 Zustände)."))

st.markdown("## ❓ Kernfrage: Reicht der Gesamtbestand, oder braucht die Bestellung das Alter?")
if cell is not None:
    kind, text = ev.verdict_headline(cell)
    getattr(st, kind)(text)

st.markdown("---")

tab_hand, tab_raster, tab_space, tab_info, tab_age, tab_cost = st.tabs([
    "1 · Handbeispiel", "2 · Raster", "3 · Zustandsraum", "4 · Was nutzt die exakte Politik?", "5 · Altersregel", "6 · Kostenzerlegung",
])

# --- 1. Handbeispiel -----------------------------------------------------------------------------------------------------------------------
with tab_hand:
    st.subheader("🔬 Handbeispiel in Brüchen: Haltbarkeit 2")
    st.markdown(
        """
Kleinste Instanz zum Nachrechnen von Hand, **unabhängig von der Seitenleiste**: Haltbarkeit 2, Lieferzeit 0, Nachfrage 0, 1 oder 2 Stück mit Wahrscheinlichkeit ¼, ½, ¼ (Mittel 1, nicht das Vehikel der übrigen Reiter),
h = 1, p = 9, **w = 5**, Bestand nach der Bestellung höchstens 2. Zustand z = Zahl der Stück mit noch einer Periode Restlebensdauer („alt“); die Bestellung a kommt frisch an.
Zulässig ist a ≤ 2 − z, also gibt es 3 · 2 · 1 = 6 Politiken (a(0), a(1), a(2)). Alle Werte sind exakte Brüche.
        """
    )
    st.markdown("**Eine Periode von Hand: ein altes und ein frisches Stück im Bestand (z = 1, a = 1)**")
    rows = []
    for d, pr in enumerate(H.PROBS):
        zf, cf_, _, _ = H.step(1, 1, d, "FIFO")
        zl, cl_, _, _ = H.step(1, 1, d, "LIFO")
        rows.append({"Nachfrage d": d, "Wahrscheinlichkeit": str(pr), "FIFO: Folgezustand z′": zf, "FIFO: Kosten": str(cf_), "LIFO: Folgezustand z′": zl, "LIFO: Kosten": str(cl_)})
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Bei d = 1 verkauft FIFO das alte Stück (das frische wird übertragen, Kosten h = 1), LIFO das frische (das alte läuft ab, Kosten w = 5).")
    summ = {r: _hand(r) for r in C.RULE_CHOICES}
    pol_choice = st.radio("Zustandsgraph für", ("exakt beste Politik", "bester Base-Stock"), horizontal=True, key="hand_policy")
    cols = st.columns(2)
    for col, rname in zip(cols, C.RULE_CHOICES):
        s = summ[rname]
        with col:
            st.markdown(f"**{rname}**")
            table = []
            for g, pol, pi, _c in s["table"]:
                tags = []
                if pol == s["opt_policy"]:
                    tags.append("Optimum")
                if pol == s["bs_policy"]:
                    tags.append("bester Base-Stock")
                table.append({"Politik a(0), a(1), a(2)": "(" + ", ".join(map(str, pol)) + ")", "Kosten (Bruch)": str(g), "Kosten (dezimal)": de(float(g), 4), "Vermerk": ", ".join(tags)})
            st.dataframe(table, hide_index=True, width="stretch")
            chosen = s["opt_policy"] if pol_choice == "exakt beste Politik" else s["bs_policy"]
            st.graphviz_chart(H.dot_source(chosen, rname), width="stretch")
    kind, text = ev.verdict_hand(summ["FIFO"], summ["LIFO"])
    getattr(st, kind)(text)
    st.caption("Der Grund in diesem Zustand: Unter LIFO nimmt die frisch bestellte Einheit den Verkauf weg, die alte läuft für w = 5 ab. Das Beispiel hat Mittel 1 und Grenze 2; die Zahlen der übrigen Reiter gelten für Mittel 3.")

# --- 2. Raster -------------------------------------------------------------------------------------------------------------------------------
with tab_raster:
    st.subheader("🔬 Raster: Lücke nach Haltbarkeit und Verfallskosten")
    st.caption("Vorgerechnet (data/vdw_grid.json). Lieferzeit wie in der Seitenleiste; FIFO und LIFO nebeneinander. Farbskala bis 12 %, größere Werte stehen als Zahl in der Zelle. Leere Zellen sind nicht gerechnet.")
    c1, c2 = st.columns(2)
    metric_name = c1.selectbox("Maß", ["Base-Stock auf dem Gesamtbestand", "Altersregel S + β·z₁", "Tabelle a(Gesamtbestand)", "Tabelle a(Gesamtbestand, z₁)"], key="raster_metric",
                               help="Lücke zur exakten Politik in Prozent der exakten Kosten. Die Tabellen sind obere Schranken aus lokaler Suche; sie gibt es nur bis Haltbarkeit 4 (Lieferzeit 0 auch 5).")
    p_ratio = c2.radio("Strafverhältnis p/h", C.P_CHOICES, index=1, horizontal=True, key="raster_p", format_func=lambda v: de(v, 0),
                       help="Standard 9. Für 4 und 19 ist nur w = 3 und 10 bei Haltbarkeit 2 bis 4 vorgerechnet, mit Bestandsgrenze 14.")
    metric = {"Base-Stock auf dem Gesamtbestand": "gap_bs", "Altersregel S + β·z₁": "gap_age", "Tabelle a(Gesamtbestand)": "gap_tab_total",
              "Tabelle a(Gesamtbestand, z₁)": "gap_tab_total_z1"}[metric_name]
    if p_ratio == 9.0:
        ms_all = list(range(2, C.GRID_M_MAX[int(lead)] + 1))
        ws_all = list(C.W_CHOICES)
    else:
        ms_all = [2, 3, 4]
        ws_all = [3.0, 10.0]
    cols = st.columns(2)
    for col, rname in zip(cols, C.RULE_CHOICES):
        with col:
            cells = [[G.lookup(int(lead), rname, ww, mm, p=p_ratio) for mm in ms_all] for ww in ws_all]
            matrix = [[(c.get(metric) if c is not None else None) for c in row] for row in cells]
            flat = [c for row in cells for c in row if c is not None]
            st.plotly_chart(build_raster(matrix, ms_all, ws_all, f"{rname}, Lieferzeit {lead}, p/h = {de(p_ratio, 0)}"), width="stretch", key=f"raster_{rname}")
            kind, text = ev.verdict_raster(flat, metric, metric_name)
            getattr(st, kind)(text)

# --- 3. Zustandsraum -----------------------------------------------------------------------------------------------------------------------
with tab_space:
    st.subheader("🔬 Zustandsraum: Kasten gegen alle Zustände gegen erreichbar")
    st.caption("Vorgerechnet. Lieferzeit, Ausgaberegel und w wie in der Seitenleiste. Logarithmische Achse.")
    rows = [c for c in (G.lookup(int(lead), rule, w, mm) for mm in range(2, C.GRID_M_MAX[int(lead)] + 1)) if c is not None]
    st.plotly_chart(build_statespace(rows), width="stretch", key="space_chart")
    st.dataframe([{"Haltbarkeit m": r["m"], "Altersklassen k": r["m"] - 1 if int(lead) == 0 else r["m"], "Kasten (T+1)^k": de_int(r["box"]), "Zustände C(T+k, k)": de_int(r["states"]),
                   "erreichbar, beliebige Bestellung": de_int(r["reach_any"]), "erreichbar unter exakter Politik": de_int(r["reach_dp"]), "erreichbar unter Base-Stock": de_int(r["reach_bs"])} for r in rows],
                 hide_index=True, width="stretch")
    if cell is not None:
        kind, text = ev.verdict_statespace(cell)
        getattr(st, kind)(text)
    st.caption("Bestandsgrenze T = 12; der Kasten (T+1)^k zählt jede Klasse einzeln bis 12, die Gesamtgrenze lässt C(T+k, k) Zustände übrig.")

# --- 4. Was nutzt die exakte Politik? -------------------------------------------------------------------------------------------------------
with tab_info:
    st.subheader("🔬 Was nutzt die exakte Politik vom Alter?")
    if cell is None:
        st.info("Für diese Zelle ist nichts gerechnet.")
    else:
        st.markdown("**Vorgerechnet:** Abstand der besten Tabellen zur exakten Politik (obere Schranken aus lokaler Suche, Koordinatenabstieg).")
        st.plotly_chart(build_gap_bars(cell), width="stretch", key="gap_bars")
        kind, text = ev.verdict_tables(cell)
        getattr(st, kind)(text)
        a_tot, n_tot = cell["amb_tot"]
        a_z1, n_z1 = cell["amb_tot_z1"]
        st.caption(f"Die exakte Politik bestellt bei {a_tot} von {n_tot} Gesamtbeständen je nach Altersverteilung verschieden; wenn die älteste Klasse z₁ bekannt ist, bei {a_z1} von {n_z1} Paaren (Gesamtbestand, z₁) noch (gezählt auf den erreichten Zuständen).")
        if not live_ok:
            st.info("Das Auffüllziel je Zustand rechnet die App nur bis 1.820 Zustände selbst (Lieferzeit 0 bis Haltbarkeit 5, Lieferzeit 1 bis 4).")
        else:
            with st.spinner("Rechne die exakte Politik der Zelle (unter einer Sekunde bis wenige Sekunden) …"):
                live = _live(int(lead), rule, w, int(m))
                targets = _targets(int(lead), rule, w, int(m))
            st.markdown("**Live gerechnet:** Auffüllziel (Gesamtbestand plus Bestellung) der exakten Politik nach Gesamtbestand und älteste Klasse z₁ (nur Zustände mit Anteil über 1e-4 der Zeit).")
            fig = build_targets(targets)
            if fig is not None:
                st.plotly_chart(fig, width="stretch", key="target_chart")
            st.caption(f"Live: Kosten der exakten Politik {de(live.g, 4)} (Zertifikat {live.cert:.0e}), vorgerechnet {de(cell['g'], 4)}. Ein Sternchen markiert Zellen, in denen Zustände mit gleichem Schlüssel verschiedene Ziele haben (dann gilt das Ziel mit dem größten Zeitanteil)."
                       + (" Bei Haltbarkeit 2 und Lieferzeit 0 ist z₁ der ganze Bestand: nur die Diagonale ist belegt." if live.P.k == 1 else ""))

# --- 5. Altersregel ---------------------------------------------------------------------------------------------------------------------------
with tab_age:
    st.subheader("🔬 Altersregel: Auffüllen auf S + β · z₁")
    st.markdown("Die Regel füllt auf das Ziel S + β · z₁ auf (z₁ = Menge der ältesten Klasse, gerundet). β = 0 ist der Base-Stock; β < 0 bestellt bei alter Ware weniger, β > 0 mehr.")
    if cell is None or not live_ok or "gap_age" not in cell:
        kind, text = ev.verdict_age_rule(cell)
        getattr(st, kind)(text if cell is not None else "Für diese Zelle ist nichts gerechnet.")
        if cell is not None:
            st.caption("Live rechnet die App die Altersregel bis Haltbarkeit 5 (Lieferzeit 0) bzw. 4 (Lieferzeit 1).")
    else:
        key = f"{int(lead)}_{rule}_{int(w)}_{int(m)}"
        s_col, b_col = st.columns(2)
        s_val = s_col.slider("Niveau S", 0, C.T_LIMIT, int(cell["age_S"]), key=f"age_s_{key}")
        b_val = b_col.slider("β", float(R.BETAS[0]), float(R.BETAS[-1]), float(cell["age_beta"]), step=0.25, key=f"age_b_{key}")
        with st.spinner("Rechne das Raster der Altersregel (169 exakte Auswertungen, bis etwa 5 Sekunden) …"):
            live = _live(int(lead), rule, w, int(m))
            grid = _age_grid(int(lead), rule, w, int(m))
        gap_now = ev.age_gap(live, int(s_val), float(b_val))
        c1, c2, c3 = st.columns(3)
        c1.metric("Lücke der gewählten Regel", de(max(gap_now, 0.0), 2, True) + " %", delta="in % der exakten Kosten", delta_color="off")
        c2.metric("Lücke des besten Base-Stock", de(max(cell["gap_bs"], 0.0), 2, True) + " %", delta="in % der exakten Kosten", delta_color="off")
        c3.metric("Lücke der besten Altersregel", de(max(cell["gap_age"], 0.0), 2, True) + " %", delta="in % der exakten Kosten", delta_color="off")
        st.plotly_chart(build_age_grid(grid, list(R.BETAS), (int(s_val), float(b_val))), width="stretch", key="age_grid")
        kind, text = ev.verdict_age_rule(cell, gap_now)
        getattr(st, kind)(text)
        st.caption("Bei LIFO und w ≥ 3 kehrt sich das Vorzeichen von β zwischen den Lieferzeiten um: bei Lieferzeit 0 β < 0, bei Lieferzeit 1 β > 0 (dort etwa ein Base-Stock auf dem Bestand ohne die älteste Klasse; bei FIFO und Lieferzeit 1 ist der schlechter als der Base-Stock auf dem Gesamtbestand). "
                   "Farbskala bis 15 %, größere Werte stehen als Zahl.")

# --- 6. Kostenzerlegung ---------------------------------------------------------------------------------------------------------------------
with tab_cost:
    st.subheader("🔬 Kostenzerlegung: wohin das Alter kostet")
    cf = G.lookup(int(lead), "FIFO", w, int(m))
    cl = G.lookup(int(lead), "LIFO", w, int(m))
    if cf is None or cl is None:
        st.info("Für diese Zelle ist nichts gerechnet.")
    else:
        st.caption("Vorgerechnet. Kosten je Periode = Lager h · (y − d)⁺ + Fehlmenge p · (d − y)⁺ + Verfall (w − h) · Ablaufmenge, y = Bestand beim Verkauf. Die Summe ist die Kostenzahl der exakten Politik bzw. des besten Base-Stock.")
        rows = []
        for cc, rname in ((cf, "FIFO"), (cl, "LIFO")):
            rows.append((f"{rname}: exakt", ev.cost_terms(cc["dp"], cc["p"], cc["w"])))
            rows.append((f"{rname}: Base-Stock S = {cc['S_bs']}", ev.cost_terms(cc["bs"], cc["p"], cc["w"])))
        st.plotly_chart(build_decomposition(rows), width="stretch", key="decomp")
        kind, text = ev.verdict_decomposition(cf, cl)
        getattr(st, kind)(text)

st.markdown("---")

with st.expander("⚠️ Annahmen, Grenzen und bekannte Probleme"):
    st.markdown(C.ASSUMPTIONS_MARKDOWN)

with st.expander("📐 Mathematische Formulierung"):
    # erklaerseite:lesehilfe:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/verderbliche-ware-erklaert.json, nicht von Hand ändern)
    st.markdown(
        r"""
**Lesehilfe.** Gegeben sind Haltbarkeit $m$, Lieferzeit $L \in \{0, 1\}$, die Nachfrageverteilung (Poisson, Mittel 3), Kosten $h$, $p$, $w$ und eine Ausgaberegel (FIFO oder LIFO). Gesucht ist die Bestellmenge $a$ je Zustand $z$, die die erwarteten Kosten je Periode minimiert, und der Abstand einfacher Regeln dazu.

| Symbol | Bedeutung |
|---|---|
| $z = (z_1, \dots, z_k)$ | Bestand je Restlebensdauer, $z_1$ = älteste Klasse; $k = m - 1$ bei $L = 0$, $k = m$ bei $L = 1$ |
| $T$ | Bestandsgrenze (12) |
| $d$ | Nachfrage einer Periode |
| $y$ | Bestand beim Verkauf (Lieferzeit 0: nach der Bestellung) |
| $A$ | Menge, die am Periodenende abläuft (Rest der ältesten Klasse nach der Ausgabe) |
| $h, p, w$ | Kosten je übertragenem, fehlendem, ablaufendem Stück |
| $g$ | erwartete Kosten je Periode |

[Schritt für Schritt erklärt, mit Herleitung und Literatur](https://sebastianhanisch.net/verderbliche-ware-erklaert.html#fachleute)
        """
    )
    # erklaerseite:lesehilfe:end
    st.markdown(
        r"""
**Gegeben und gesucht.** Gegeben sind Haltbarkeit $m$, Lieferzeit $L \in \{0, 1\}$, die Nachfrageverteilung (Poisson, Mittel 3), Kosten $h$, $p$, $w$ und eine Ausgaberegel (FIFO oder LIFO). Gesucht ist die Bestellmenge $a$ je Zustand $z$, die die erwarteten Kosten je Periode minimiert, und der Abstand einfacher Regeln dazu.

| Symbol | Bedeutung |
|---|---|
| $z = (z_1, \dots, z_k)$ | Bestand je Restlebensdauer, $z_1$ = älteste Klasse; $k = m - 1$ bei $L = 0$, $k = m$ bei $L = 1$ |
| $T$ | Bestandsgrenze (12) |
| $d$ | Nachfrage einer Periode |
| $y$ | Bestand beim Verkauf (Lieferzeit 0: nach der Bestellung) |
| $A$ | Menge, die am Periodenende abläuft (Rest der ältesten Klasse nach der Ausgabe) |
| $h, p, w$ | Kosten je übertragenem, fehlendem, ablaufendem Stück |
| $g$ | erwartete Kosten je Periode |

Mehr dazu im Abschnitt „Annahmen, Grenzen und bekannte Probleme“.

**Periodenkosten.** Übertragen werden die Stücke, die nach dem Verkauf bleiben und nicht ablaufen; ablaufende Stücke kosten $w$ statt $h$:

$$c(z, a, d) = h\,(y - d)^+ + p\,(d - y)^+ + (w - h)\,A$$

**Zustandszahl.** Mit Gesamtgrenze $T$ und $k$ Altersklassen:

$$|\mathcal{Z}| = \binom{T + k}{k}$$

**Exakte Politik (Bellman-Gleichung, Durchschnittskosten).** Gelöst wird sie mit relativer Wertiteration auf der trägen Kette $P' = \tfrac12 P + \tfrac12 I$ (gleiche optimale Politik, Aperiodizität):

$$g + v(z) = \min_{a}\Big\{\bar c(z, a) + \sum_{z'} P(z' \mid z, a)\, v(z')\Big\}$$

**Auswertung einer festen Regel $\mu$** über die stationäre Verteilung der von leer erreichbaren Zustände:

$$\pi = \pi P_\mu, \qquad \sum_z \pi(z) = 1, \qquad g(\mu) = \sum_z \pi(z)\,\bar c\big(z, \mu(z)\big)$$

**Base-Stock und Altersregel.** Mit Gesamtbestand $\sum_i z_i$ und gerundetem Ziel:

$$a(z) = \max\Big\{0,\ \big\lfloor S + \beta\, z_1 + \tfrac12 \big\rfloor - \sum_i z_i\Big\}$$

$\beta = 0$ ist der Base-Stock auf dem Gesamtbestand.

**Lücke** einer Regel $\mu$ (Bezug: exakte Kosten $g^*$):

$$\text{Lücke}(\mu) = 100 \cdot \Big(\frac{g(\mu)}{g^*} - 1\Big)\ \%$$

**Literatur.** Zustand nach Restlebensdauer und FIFO-Ausgabe bei Lieferzeit 0 unter Base-Stock-Politiken (minimiert die Ablaufmenge): Zhang, Ayer, White (2016), arXiv 1605.01442, Vorfassung (Volltext gelesen). Die Messungen dieser Demo sind eigene Rechnungen.
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Bestandspolitiken: von Base-Stock bis Regelwahl](https://sebastianhanisch.net/konzepte-bestandspolitiken.html)."
)
