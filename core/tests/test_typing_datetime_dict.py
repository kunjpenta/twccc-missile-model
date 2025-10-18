from core.typing import DateTimeDict


def test_datetime_dict_shape():
    payload: DateTimeDict = {
        "day": 17, "month": 10, "year": 2025,
        "hour": 12, "minutes": 34, "seconds": 56,
    }
    # at runtime it's a plain dict; this just ensures the keys are present
    assert set(payload.keys()) == {"day", "month",
                                   "year", "hour", "minutes", "seconds"}
