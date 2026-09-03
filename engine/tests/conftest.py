"""Shared fixtures. Everything here is cheap and cached across the session."""

from __future__ import annotations

import pytest

from skurious import geo, sky as sky_mod
from skurious.sidereal import Scheme
from skurious.time import instant

EDISON = 5097529          # GeoNames id; an Indian-diaspora town in New Jersey


@pytest.fixture(scope="session")
def scheme() -> Scheme:
    return Scheme()


@pytest.fixture(scope="session")
def edison():
    return geo.by_id(EDISON)


@pytest.fixture(scope="session")
def kurukshetra():
    return geo.resolve("kurukshetra")


@pytest.fixture(scope="session")
def wedding_instant(edison):
    return instant("2019-02-14", "19:30", edison)


@pytest.fixture(scope="session")
def wedding_sky(edison, wedding_instant, scheme):
    return sky_mod.build(edison, wedding_instant, scheme)
