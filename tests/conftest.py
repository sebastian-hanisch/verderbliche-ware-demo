"""Gemeinsame Fixtures: die Mini-Instanz, an der jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b).

Handbeispiel: Haltbarkeit 2, Lieferzeit 0, Nachfrage 0 / 1 / 2 mit 1/4, 1/2, 1/4, h = 1, p = 9, w = 5, Bestand nach der Bestellung höchstens 2.
Zustand z = Stück mit noch einer Periode Restlebensdauer. Die Rechnung steht in README und im ersten Reiter der App."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vdw_algorithm import Perishable, Settings  # noqa: E402

HAND_DEMAND = (0.25, 0.5, 0.25)


def hand_settings(rule: str, **kw) -> Settings:
    base = dict(m=2, lead=0, rule=rule, w=5.0, T=2, demand=HAND_DEMAND)
    base.update(kw)
    return Settings(**base)


@pytest.fixture
def hand_fifo():
    return Perishable(hand_settings("FIFO"))


@pytest.fixture
def hand_lifo():
    return Perishable(hand_settings("LIFO"))
