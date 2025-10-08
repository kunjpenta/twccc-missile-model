# core/tests/test_units_geodesy.py

from core.utils.geodesy import LatLon, haversine_distance_m, initial_bearing_deg
from django.test import SimpleTestCase

from core.utils.geodesy import (
    destination_point,
    enu_from_latlon,

    latlon_from_enu,
)
from core.utils.units import kts_to_mps, m_to_nm, mps_to_kts, nm_to_m


class UnitsGeodesyTests(SimpleTestCase):
    def test_units(self):
        self.assertAlmostEqual(mps_to_kts(100), 194.384, delta=0.1)
        self.assertAlmostEqual(kts_to_mps(194.384), 100, delta=0.2)
        self.assertAlmostEqual(m_to_nm(1852), 1.0, delta=1e-6)
        self.assertAlmostEqual(nm_to_m(1.0), 1852.0, delta=1e-6)

    def test_geo(self):
        DELHI = LatLon(28.6139, 77.2090)
        AGRA = LatLon(27.1767, 78.0081)

        d_m = haversine_distance_m(DELHI, AGRA)
        self.assertTrue(170_000 <= d_m <= 190_000)  # loose band

        br = initial_bearing_deg(DELHI, AGRA)
        self.assertTrue(140 <= br <= 165)  # allow method variance

        p2 = destination_point(DELHI, br, d_m)
        # Should land very close to AGRA
        d2 = haversine_distance_m(p2, AGRA)
        self.assertLess(d2, 2000)  # <2 km

        e, n = enu_from_latlon(AGRA, DELHI)
        p3 = latlon_from_enu(e, n, DELHI)
        self.assertLess(haversine_distance_m(p3, AGRA), 50)  # <50 m


def test_haversine_distance():
    p1 = LatLon(28.6139, 77.2090)
    p2 = LatLon(27.1767, 78.0081)
    distance = haversine_distance_m(p1, p2)
    assert distance > 0


def test_initial_bearing():
    p1 = LatLon(28.6139, 77.2090)
    p2 = LatLon(27.1767, 78.0081)
    bearing = initial_bearing_deg(p1, p2)
    assert 0 <= bearing < 360
