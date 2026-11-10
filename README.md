# Verderbliche Ware: Zustand = Alter – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-verderbliche-ware-demo.streamlit.app/)**

Demo der Reihe **Bestandspolitiken** in der „Konzepte“-Reihe für die Website „Sebastian Hanisch – Operations Research und Machine Learning“. Sie knüpft an Demos an, bei denen der Zustand eine einzige Zahl ist (Bestand oder Bestandsposition): Hier hat Ware eine **feste Haltbarkeit**, der Zustand ist der Bestand je Restlebensdauer, und die Frage lautet, ob die Bestellregel dieses **Alter** kennen muss. Gerechnet wird die beste Bestellpolitik exakt (relative Wertiteration über alle Altersverteilungen) und mit einfachen Regeln verglichen. Eine Periode ohne Alterung behandelt `newsvendor-evpi-demo`; Prognose und Base-Stock aus der Prognose `forecast-inventory-demo`.

## Warum dieses Problem

Naheliegend ist die Erwartung, dass bei verderblicher Ware der Zustand mit der Haltbarkeit wächst und einfache Regeln auf dem Gesamtbestand deutlich verlieren. Diese Demo prüft das an einem festen Vehikel (siehe Modell) und findet ein differenzierteres Bild: **Das Alter kostet bei der Bestellregel vor allem dann etwas, wenn die Ausgaberegel es ungenutzt lässt (LIFO).** Mit FIFO-Ausgabe und Lieferzeit 0 ist der beste Base-Stock auf dem Gesamtbestand in 26 von 30 Zellen exakt optimal (Haltbarkeit 2 bis 7, w = 0, 1, 3, 10, 30; Ausnahmen bei Haltbarkeit 2 und 3 mit Lücken von +0,36 bis +1,36 %). Mit LIFO-Ausgabe und Lieferzeit 0 liegt er bei w ≥ 3 zwischen +0,05 und +26,69 % über den exakten Kosten, und eine Regel mit einem zusätzlichen Alterswert (der Menge der ältesten Klasse) schließt in den 15 Zellen mit Haltbarkeit 3 bis 5 (Lieferzeit 0) bzw. 3 und 4 (Lieferzeit 1) 13 bis 98 % dieser Lücke, bei Haltbarkeit 2 und Lieferzeit 0 die ganze. Bei Lieferzeit 1 ist die Lücke bei FIFO ab Haltbarkeit 4 überwiegend der Effekt der Lieferzeit mit verlorener Nachfrage, nicht des Alters; bei Haltbarkeit 2 (und 3 mit w = 30) liegt sie deutlich darüber (bis +9,18 %).

## Modell

Ein Artikel, **Poisson-Nachfrage mit Mittel 3** je Periode (bei 16 gekappt), **h = 1** je am Periodenende übertragenem Stück, **p = 9** je nicht bedientem Stück (kritisches Verhältnis 0,9), **w** je am Periodenende ablaufendem Stück (w = 0, 1, 3, 10, 30), keine Bestellkosten, **verlorene Nachfrage**, **feste Haltbarkeit m** (2 bis 7 Perioden), **Bestandsgrenze 12**, **Lieferzeit** 0 oder 1, Ausgaberegel **FIFO** (ältestes zuerst) oder **LIFO** (frischestes zuerst).

**Kostenkonvention (zuerst lesen).** h fällt nur auf **übertragene** Stücke; ein ablaufendes Stück kostet w und kein h. Daraus folgt: Bei **w = 0 ist LIFO billiger als FIFO** (ablaufende Ware kostet nichts, Lieferzeit 0: −24,37 bis −2,91 %, Lieferzeit 1: −25,57 bis −7,76 %, Bezug: exakte Kosten FIFO). Das ist eine Folge der Konvention, keine Aussage über Frischware; die Schlagzeilen dieser README gelten für w ≥ 1.

Zustand z = (z₁, …, z_k): Stück mit noch 1, …, k Perioden Restlebensdauer, z₁ ist die älteste Klasse. Bei Lieferzeit 0 ist k = m − 1 (die Bestellung kommt frisch an und wird in derselben Periode verkauft), bei Lieferzeit 1 ist k = m. Mit Gesamtgrenze 12 gibt es C(12 + k, k) Zustände (Kasten ohne Gesamtgrenze: 13^k). Periodenkosten (Lieferzeit 0, y = Bestand nach der Bestellung, A = ablaufende Menge): h·(y − d)⁺ + p·(d − y)⁺ + (w − h)·A; die Zerlegung zeigt der letzte Reiter der App. Formeln im Expander „📐 Mathematische Formulierung“.

## Methodik

- **Exakte Politik:** relative Wertiteration auf der trägen Kette P′ = ½P + ½I (gleiche optimale Politik, aperiodisch). Ohne sie bleibt die Iteration bei Lieferzeit 1, LIFO, Haltbarkeit 2 und w = 3 hängen (Zertifikat nach 2.000 Iterationen über 0,1, mit träger Kette unter 1e-10 nach weniger als 100); bei w = 10 und 30 konvergiert sie auch ohne träge Kette. Zertifikat = Spannweite der Bellman-Differenz; es liegt in allen 182 vorgerechneten Zellen unter 1e-10.
- **Regeln auf dem Gesamtbestand:** Base-Stock (Auffüllen auf S), exakt ausgewertet über die stationäre Verteilung der von leer erreichbaren Zustände. Der **Q-Abstand** der Base-Stock-Bestellung zur besten Bestellung im selben Zustand ist 0, wenn die exakte Politik dort dasselbe bestellt.
- **Altersregel:** Auffüllen auf S + β·z₁ (gerundet), β von −2 bis +1 in Vierteln, S von 0 bis 12 (169 Auswertungen); β = 0 ist der Base-Stock.
- **Tabellen:** beste Bestellmenge je Gesamtbestand und je (Gesamtbestand, z₁), gesucht per Koordinatenabstieg. Das sind **obere Schranken** der besten Tabelle, kein Beweis.
- **Rechenlast:** Bis Haltbarkeit 5 (Lieferzeit 0) bzw. 4 (Lieferzeit 1), also höchstens 1.820 Zustände, rechnet die App selbst; alles Größere und die Tabellen liegen in `data/vdw_grid.json` (182 Zellen, erzeugt mit `vdw_grid.py`, unter 1 MB). Die Tests rechnen kleine Zellen neu und vergleichen.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen gelten für das Modell oben (Mittel 3, h = 1, p = 9, Grenze 12; das Strafverhältnis-Raster mit Grenze 14), exakte DP, die Lücke in Prozent der **exakten Kosten**. „Zellen“ sind Kombinationen aus Haltbarkeit und w je Lieferzeit und Regel (Lieferzeit 0: 30, Lieferzeit 1: 25). Die Tabelle nennt je Befund den Test, der genau diese Zählung prüft („Zahl → Test“).

| Befund | Test |
|---|---|
| Lieferzeit 0, FIFO: der beste Base-Stock ist in **26 von 30** Zellen exakt (Lücke unter 0,005 %, Q-Abstand 0). Ausnahmen: Haltbarkeit 2 mit w = 0 (+1,25 %), w = 10 (+0,36 %), w = 30 (+1,36 %) und Haltbarkeit 3 mit w = 30 (+1,01 %) | `test_k1_lead0_fifo_base_stock_is_exact_in_26_of_30_cells_with_four_exceptions` |
| Lieferzeit 0, LIFO: bei w = 1 = h exakt in 6 von 6 Zellen; bei w = 3 fällt die Lücke mit der Haltbarkeit (+3,80 / 1,50 / 0,63 / 0,26 / 0,11 / 0,05 % für m = 2 bis 7), bei w = 10 (+6,15 bis +9,61 %) und w = 30 (+11,86 bis +26,69 %) nicht; über die 18 Zellen mit w ≥ 3: +0,05 bis +26,69 % | `test_k2_lead0_lifo_gaps_by_w` |
| Lieferzeit 0, LIFO, w = 0: Lücken +1,37 / 0,30 / 0,55 / 0,95 / 0,72 / 0,37 % (m = 2 bis 7), Randfall der Kostenkonvention | `test_k3_lead0_w_zero_lifo_gaps_are_small_but_not_zero` |
| Erwartete Ablaufmenge je Periode unter Base-Stock S = 5 (Lieferzeit 0, Haltbarkeit 2 bis 5): FIFO 0,3446 / 0,0566 / 0,0076 / 0,0009, LIFO 0,832 / 0,441 / 0,267 / 0,174. Passt zur Kostenzerlegung, in der das Alter nur über (w − h)·Ablaufmenge eingeht | `test_k4_expected_waste_at_base_stock_5_fifo_against_lifo` |
| Altersregel S + β·z₁, LIFO, w = 3, Haltbarkeit 3 bis 5: schließt **93 bis 98 %** der Base-Stock-Lücke bei Lieferzeit 0 (Rest +0,04 / 0,03 / 0,02 %), **80 bis 82 %** bei Lieferzeit 1 (Haltbarkeit 3 und 4) | `test_k5_age_rule_closes_93_to_98_percent_at_w3_lead0_and_80_to_82_at_lead1` |
| Dieselbe Regel bei w = 10 und 30 (LIFO, 10 Zellen: Lieferzeit 0 Haltbarkeit 3 bis 5, Lieferzeit 1 Haltbarkeit 3 und 4): nur **13 bis 76 %**; bei Lieferzeit 0, w = 30 und Haltbarkeit 3 bis 5 liegt β am Rand des Rasters (−2) | `test_k5b_age_rule_closes_13_to_76_percent_at_w_10_and_30` |
| Vollständig geschlossen wird die Lücke in den gerechneten Zellen nur bei Haltbarkeit 2 (Lieferzeit 0, LIFO, w = 3, 10, 30; auch Lieferzeit 1, LIFO, w = 30); in den 15 Zellen mit Haltbarkeit 3 bis 5 (Lieferzeit 0) bzw. 3 und 4 (Lieferzeit 1) bleiben +0,02 bis +7,21 % | `test_k5c_age_rule_closes_everything_only_at_shelf_life_2_lead0_never_for_m_3_to_5` |
| Das Vorzeichen von β kehrt sich um: Lieferzeit 0 β < 0 in 12 von 12 Zellen (LIFO, w ≥ 3, Haltbarkeit 2 bis 5), Lieferzeit 1 β > 0 in 9 von 9 (Haltbarkeit 2 bis 4) | `test_k5d_sign_of_beta_flips_between_lead_times` |
| Lieferzeit 1, FIFO: „Base-Stock auf dem Bestand ohne die älteste Klasse“ (β = +1) ist in 15 von 15 Zellen (Haltbarkeit 2 bis 4) schlechter als der Base-Stock | `test_k5e_base_stock_on_stock_without_oldest_class_hurts_with_fifo_at_lead1` |
| Tabelle nach dem Gesamtbestand allein: Lieferzeit 0, FIFO höchstens +0,01 % (20 Zellen); Lieferzeit 0, LIFO bis +10,96 % (20 Zellen); Lieferzeit 1, FIFO höchstens +0,42 % (15 Zellen); Lieferzeit 1, LIFO bis +5,88 % (15 Zellen). In einzelnen Zellen besser als die Altersregel (Lieferzeit 0, LIFO, w = 10: Haltbarkeit 4 +2,60 gegen +4,70 %, Haltbarkeit 5 +3,28 gegen +3,70 %) | `test_k6_table_by_total_alone` |
| Tabelle nach (Gesamtbestand, älteste Klasse), LIFO, höchstens Haltbarkeit 4: bei w = 3 höchstens +0,04 % (6 Zellen, beide Lieferzeiten); bei w = 10 bis +0,48 % (Lieferzeit 0) bzw. +1,65 % (Lieferzeit 1). Obere Schranke aus lokaler Suche, kein Beweis, dass genau z₁ genügt | `test_k6b_table_by_total_and_oldest_class` |
| Lieferzeit 1, FIFO: Base-Stock-Lücke +1,36 bis +9,18 % in 25 Zellen, nie exakt; bei Haltbarkeit 6 +1,74 bis +1,86 %, nahe der Referenz ohne Verfall (+1,75 %, eigene kleine DP, Lieferzeit 1, verlorene Nachfrage, Mittel 3) | `test_k7_lead1_fifo_gap_is_mostly_the_lead_time_effect`, `test_o7_reference_without_spoilage_lead_one_gap_is_about_1_75_percent` |
| Lieferzeit 1, LIFO: Lücke bis +57,98 % (Haltbarkeit 2, w = 0, die einzige Zelle, in der der Base-Stock an die Bestandsgrenze stößt); bei w = 3 +24,16 / 10,93 / 8,05 / 5,73 / 4,53 % für Haltbarkeit 2 bis 6 | `test_k7b_lifo_lead1_gaps_reach_58_percent_at_w0_and_short_shelf_life` |
| Die Ausgaberegel zählt mehr als die Wahl zwischen Base-Stock und exakter Bestellpolitik: exakte Kosten LIFO gegen FIFO **+5,05 bis +74,14 %** bei w ≥ 3 (33 Zellen, beide Lieferzeiten); bei w = 1 = h und Lieferzeit 0 kostengleich in 6 von 6 Zellen, bei Lieferzeit 1 nicht (+0,64 / −2,15 / −2,41 / −1,96 / −1,48 %) | `test_k8_rule_matters_more_than_the_order_rule`, `test_o6c_with_w_equal_h_lead_zero_every_rule_costs_the_newsvendor_value` |
| w = 0: LIFO billiger als FIFO (Konvention): Lieferzeit 0 −24,37 bis −2,91 % (6 Zellen), Lieferzeit 1 −25,57 bis −7,76 % (5 Zellen) | `test_k8b_w_zero_lifo_is_cheaper_by_construction_of_the_cost_convention` |
| Zustandszahl C(12 + k, k) bei Lieferzeit 0: 13, 91, 455, 1.820, 6.188, 18.564 (Haltbarkeit 2 bis 7; Kasten 13 bis 4.826.809); erreichbar unter der exakten Politik (w = 3, beide Regeln) 6, 21, 56, **126**, 252, 462. Lieferzeit 1: 91 bis 18.564 (Haltbarkeit 2 bis 6), erreichbar (w = 3) FIFO 20 / 107 / 463 / 1.535 / 4.058, LIFO 9 / 91 / 245 / 1.006 / 2.407 | `test_k9_state_counts` |
| Bestandsgrenze 12: Randmasse der exakten Politik unter 1e-4 in 110 von 110 Zellen; beim Base-Stock eine Ausnahme (Lieferzeit 1, LIFO, Haltbarkeit 2, w = 0, S = 12), dort ist das Ergebnis (+57,98 %) mit Grenze 16 und 20 identisch. Nachfrage über 16 hat Wahrscheinlichkeit 2,2e-8 | `test_k10_boundary_mass_zero_for_the_exact_policy_and_one_exception_for_base_stock`, `test_k10b_the_one_exception_is_identical_with_limit_16_and_20`, `test_k10c_poisson_tail_above_16_is_2e_8` |
| Strafverhältnis p/h = 4, 9, 19 (Grenze 14, w = 3 und 10, Haltbarkeit 2 bis 4, je 6 Zellen): Lieferzeit 0, FIFO größte Base-Stock-Lücke +0,79 / +0,36 / +0,26 %, LIFO +12,91 / +9,61 / +6,44 %; Lieferzeit 1, FIFO +7,75 / +6,69 / +7,93 % (Tabelle nach Gesamtbestand höchstens +0,05 / +0,42 / +0,42 %), LIFO +15,13 / +24,16 / +37,66 % | `test_k11_penalty_ratio_grid` |
| Beschreibung der exakten Politik (Lieferzeit 0, LIFO, Haltbarkeit 3, w = 10): Auffüllziel 5 bei leerem Lager, 4 ohne Ware der ältesten Klasse (Bestand 1 bis 4), 3 mit älterer Ware bei Bestand bis 3, wieder 4 bei Bestand 4. Lieferzeit 1, LIFO, Haltbarkeit 3, w = 3, Bestand 8: Ziel 8 / 9 / 10 / 11 für z₁ = 0 bis 3 | `test_k12_dp_target_levels` |
| Träge Kette nötig, Zertifikate unter 1e-10 | `test_k13_lazy_chain_is_needed_for_lead1_lifo_shelf_life_2`, `test_k13b_certificates_are_below_1e_10_in_all_cells` |
| Text der Annahmen in README und App gleich; jeder Test dieser Tabelle existiert | `test_readme_assumptions_text_is_the_apps_text`, `test_readme_test_table_names_existing_tests` |

**Handbeispiel von Hand** (Haltbarkeit 2, Lieferzeit 0, Nachfrage 0 / 1 / 2 mit ¼, ½, ¼, Mittel 1, h = 1, p = 9, w = 5, Bestand nach der Bestellung höchstens 2; nicht das Vehikel, nur zum Nachrechnen): Zustand z = Stück mit noch einer Periode Restlebensdauer. Für z = 1, a = 1: FIFO verkauft bei d = 1 das alte Stück (Kosten 1, z′ = 1), LIFO das frische (das alte läuft ab, Kosten 5, z′ = 0). Stationär mit Base-Stock S = 2 kostet FIFO 25/13 ≈ 1,923, LIFO 59/23 ≈ 2,565; die Politik „bei einer alten Einheit nicht nachbestellen“ (2, 0, 0) kostet unter LIFO 16/7 ≈ 2,286, das ist das LIFO-Optimum. Der Base-Stock liegt unter LIFO **+12,23 %** über dem Optimum, unter FIFO bei 0. Geprüft in Brüchen und gegen den Kern in `test_hand_exact_fractions` und `test_core_evaluate_matches_hand_fractions` (`tests/test_algorithm.py`).

## Ehrliche Grenzen

- **Verdikte der App sind Messungen dieses Modells.** Jede Aussage gilt für ein Mittel (3), Poisson-Nachfrage, h = 1, p = 9 (4 und 19 nur eingeschränkt), Bestandsgrenze 12 und die dort gerechneten Zellen.
- **Orakel-Nachweise** (siehe Verifikation) sichern den Rechenkern; die Deutung „weil“ (etwa warum LIFO das Alter kostet) ist in der App und hier nur als Kostenzerlegung und Messung belegt, nicht als Beweis.

Dieselbe Liste führt die App im Ausklapper „⚠️ Annahmen, Grenzen und bekannte Probleme“ (ein Test vergleicht den Text):

- **Modell.** Ein Artikel, Poisson-Nachfrage mit Mittel 3 je Periode (bei 16 gekappt, Wahrscheinlichkeit darüber 2,2e-8), h = 1 je übertragenem Stück, p = 9 je nicht bedientem Stück (4 und 19 nur vorgerechnet), keine Bestellkosten, verlorene Nachfrage, feste Haltbarkeit, Bestandsgrenze 12. Alle Zahlen gelten nur für diese Voraussetzungen.
- **Kostenkonvention.** h fällt nur auf **übertragene** Stücke, w auf ablaufende. Bei w = 0 ist LIFO deshalb billiger als FIFO (ablaufende Ware kostet nichts): eine Folge der Konvention, keine Aussage über Frischware. Schlagzeilen gelten für w ≥ 1.
- **Ausgaberegel fest.** FIFO und LIFO sind vorgegebene Regeln, nicht Teil der Optimierung. Ein gemeinsames Optimum über Ausgabe- und Bestellregel ist nicht gerechnet. LIFO steht als Modell für „die Kundschaft greift nach hinten“; das ist eine Deutung, nicht gemessen.
- **Bestandsgrenze 12.** Die exakte Politik berührt sie in keiner der 110 Zellen (Randmasse 0). Einzige Auffälligkeit: Lieferzeit 1, LIFO, Haltbarkeit 2, w = 0, dort stößt der beste Base-Stock (S = 12) an die Grenze; das Ergebnis ist mit Grenze 16 und 20 identisch.
- **Tabellen nach Alter sind obere Schranken.** Die besten Tabellen a(Gesamtbestand) und a(Gesamtbestand, älteste Klasse) stammen aus einer lokalen Suche (Koordinatenabstieg), nicht aus einem Beweis. „Die DP braucht genau die älteste Klasse“ ist daraus nicht abzuleiten.
- **Altersregel.** Das Raster der Regel „Auffüllen auf S + β·z₁“ reicht von β = −2 bis +1 in Vierteln; bei Lieferzeit 0, LIFO, w = 30 und Haltbarkeit 3 bis 5 liegt das beste β am Rand (−2). In den 15 Zellen mit Haltbarkeit 3 bis 5 (Lieferzeit 0) bzw. 3 und 4 (Lieferzeit 1) schließt sie 13 bis 98 % der Lücke (Rest +0,02 bis +7,21 %); bei Haltbarkeit 2 und Lieferzeit 0 schließt sie die Lücke bei LIFO und w = 3, 10, 30 vollständig.
- **Lieferzeit 1.** Bei FIFO ist die Lücke ab Haltbarkeit 4 überwiegend der Effekt der Lieferzeit mit verlorener Nachfrage (ohne Verfall +1,75 % im selben Modell), nicht des Alters; bei Haltbarkeit 2 (und 3 mit w = 30) liegt sie deutlich darüber (bis +9,18 %). Das ist ein Vergleich mit dem Modell ohne Verfall, keine Messung der Ursache.
- **Rechenlast.** Bis Haltbarkeit 5 (Lieferzeit 0) bzw. 4 (Lieferzeit 1) rechnet die App DP, Base-Stock und Altersregel selbst. Alles Größere, die Tabellen und das Strafverhältnis-Raster sind vorgerechnet (Datei `data/vdw_grid.json`, Erzeugung mit `vdw_grid.py`).
- **Literatur.** Zustand nach Restlebensdauer und die Aussage, dass bei Lieferzeit 0 unter Base-Stock-Politiken FIFO-Ausgabe die Ablaufmenge minimiert (und bei Verfallskosten w ≥ h kostenoptimal ist), nach der arXiv-Vorfassung von Zhang, Ayer und White (2016, Volltext gelesen; die Zeitschriftenfassung nicht). Das dort zitierte Original von Chazan und Gal (1977) ist nicht gelesen. Der Abstand des Base-Stock zum Optimum je Ausgaberegel ist Messung dieser Demo, keine Literaturaussage.

## Verifikation

- **Kern:** Einheiten von Hand gerechnet (`tests/test_algorithm.py`: Ausgabe FIFO/LIFO, Zustandszahlen C(T+k, k), eine Periode des Handbeispiels, stationäre Verteilung in Brüchen, Kostenzerlegung); Randfälle (`tests/test_edge_cases.py`: Haltbarkeit 2, Grenze 1, nie Nachfrage, w = 0, Gleichstände, Rundung der Altersregel).
- **Orakel** (`tests/test_oracle_verderbliche_ware.py`, anderer Rechenweg als der Kern): Einheiten-Referenz mit Listen einzelner Stücke gegen die Vektoroperationen (Übergänge und Kosten, alle Zustände × Bestellmengen × Nachfragen, beide Lieferzeiten und Regeln, Haltbarkeit 2 und 3); dichte Lösung gegen sparse Lösung; Aufzählung aller Politiken winziger Instanzen gegen die DP; Simulation auf Einheitenebene (vier Zufalls-Seeds); Howard-Politikiteration gegen Wertiteration; Newsvendor-Identität bei w = h; Referenz ohne Verfall; Ablaufmenge FIFO gegen LIFO; Abbruchregel der Base-Stock-Suche gegen volle Suche.
- **Zweig-Test:** FIFO und LIFO unterscheiden sich auf jeder geprüften Instanz in mindestens einer Zeile und sind bei höchstens einer belegten Klasse gleich; die Altersregel mit β = 0 ist der Base-Stock, mit β ≠ 0 ändert sie das Ergebnis (`tests/test_edge_cases.py`, `tests/test_claims.py`).
- **Vorgerechnete Datei:** `tests/test_grid.py` prüft Aufbau, innere Widersprüche und rechnet fünf kleine Zellen neu.
- **Claims:** `tests/test_claims.py` (Tabelle „Befunde“ oben).
- **Verdikte:** `tests/test_verdicts.py` an handgesetzten Zellen (jede Schwelle, jede Zahl im Text).
- **Oberfläche:** AppTest aller Reiter, jedes Presets mit erwarteter Verdikt-Zeile, Ränder, Permalink, nicht gerechnete Zelle (`tests/test_app_content.py`, `tests/test_app.py`); Layout (`tests/test_layout.py`), Footer, Laufzeit-Importe.
- **Umfang:** 144 Tests, rund 35 Sekunden Laufzeit (gemessen auf einem Entwicklungsrechner, je nach Rechnerlast länger).

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App: sechs Reiter, Annahmen-Ausklapper, Formeln |
| `data/vdw_grid.json` | vorgerechnetes Raster: 182 Zellen (110 Hauptraster, 72 Strafverhältnis-Raster) |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `vdw_algorithm.py` | Kern: Zustandsraum, Übergänge, Kosten, exakte Wertiteration, exakte Auswertung |
| `vdw_constants.py` | Regler, feste Annahmen, Farben, Presets, Annahmen-Text |
| `vdw_evaluation.py` | Kennzahlen, Verdikte als reine Funktionen, Live-Rechnung, Zahlenformat |
| `vdw_grid.py` | Erzeugung (Kommandozeile) und Zugriff auf das vorgerechnete Raster |
| `vdw_hand.py` | Handbeispiel in exakten Brüchen, Zustandsgraph |
| `vdw_layout.py` | Fester Kopf (Stylesheet) |
| `vdw_presets.py` | Permalink (Begrenzen, Einrasten), Presets (Schnellstart in der Seitenleiste, aktives Preset hervorgehoben) |
| `vdw_rules.py` | Base-Stock, Altersregel, Tabellen (Koordinatenabstieg), Auffüllziele |
| `vdw_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `tests/` | Kern, Orakel, Randfälle, vorgerechnete Datei, Claims, Verdikte, Presets, Layout, App, Footer, Laufzeit-Importe |

## Bewusst nicht umgesetzt

- **Kein gemeinsames Optimum über Ausgabe- und Bestellregel:** FIFO und LIFO sind feste Regeln.
- **Keine Bestellkosten, keine zufällige Haltbarkeit, keine Nachfrageverteilung außer Poisson mit Mittel 3.**
- **Keine Altersregel mit mehr als einem Alterswert** und keine Tabelle nach der ganzen Altersverteilung für Haltbarkeit über 4 (Rechenaufwand).
- **Kein Lernverfahren** (Politikgradient o. Ä.) für den Altersvektor.
- **Kein PDF-Export.**

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Das vorgerechnete Raster neu erzeugen (die vorgerechnete Datei nennt 241 s Gesamtlaufzeit, je nach Rechner, Prozesszahl und Last):

```bash
python vdw_grid.py --out data/vdw_grid.json --jobs 2
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, NumPy und SciPy.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Bestandspolitiken: von Base-Stock bis Regelwahl](https://sebastianhanisch.net/konzepte-bestandspolitiken.html).
