# core/test/quick_check.py


from core.utils.geodesy import (
    LatLon,
    destination_point,
    enu_from_latlon,
    haversine_distance_m,
    initial_bearing_deg,
    latlon_from_enu,
)
from core.utils.units import kts_to_mps, m_to_nm, mps_to_kts, nm_to_m


def main():
    assert abs(mps_to_kts(100) - 194.384) < 0.05
    assert abs(kts_to_mps(194.384) - 100) < 0.1
    assert abs(m_to_nm(1852) - 1.0) < 1e-6
    assert abs(nm_to_m(1.0) - 1852) < 1e-6
    print("Units OK")

    DELHI = LatLon(28.6139, 77.2090)
    AGRA = LatLon(27.1767, 78.0081)

    d_m = haversine_distance_m(DELHI, AGRA)
    print("Delhi–Agra distance (km) ≈", round(d_m/1000, 1))

    br = initial_bearing_deg(DELHI, AGRA)
    print("Initial bearing (deg) ≈", round(br, 1))

    p2 = destination_point(DELHI, br, d_m)
    print("Destination approx (lat, lon) ≈",
          round(p2.lat, 4), round(p2.lon, 4))

    e, n = enu_from_latlon(AGRA, DELHI)
    p3 = latlon_from_enu(e, n, DELHI)
    err_m = haversine_distance_m(p3, AGRA)
    print("ENU↔LL round-trip error (m) ≈", round(err_m, 2))


if __name__ == "__main__":
    main()
