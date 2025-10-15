# tewa/services/charting.py
from __future__ import annotations

import io
from datetime import date, datetime
from typing import (
    Iterable,
    List,
    Optional,
    Sequence,  # at top if you prefer Sequence typing
    Tuple,
)

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # headless must be set before importing pyplot


def _moving_avg(values: Sequence[float], k: Optional[int]) -> List[float]:
    if not k or k <= 1:
        return [float(v) for v in values]
    out: List[float] = []
    s = 0.0
    for i, v in enumerate(values):
        s += float(v)
        if i >= k:
            s -= float(values[i - k])
        n = min(i + 1, k)
        out.append(s / n)
    return out


def _to_datetime_list(xs: Iterable[object]) -> List[datetime]:
    out: List[datetime] = []
    for t in xs:
        if isinstance(t, datetime):
            out.append(t)
        elif isinstance(t, date):
            out.append(datetime(t.year, t.month, t.day))
        else:
            # last resort: let matplotlib try to coerce strings, but keep typing happy
            # (you can extend this if you expect strings)
            raise TypeError(f"Unsupported x value type: {type(t)!r}")
    return out


def render_score_history_png(
    series: Iterable[Tuple[object, float]],
    *,
    width: int = 800,
    height: int = 300,
    smooth: Optional[int] = None,
) -> bytes:
    dpi = 100
    fig_w, fig_h = width / dpi, height / dpi

    # Split series
    xs_raw: List[object] = [t for t, _ in series]
    ys: List[float] = [float(s) for _, s in series] if xs_raw else []

    # Convert x-values (datetime/date) to Matplotlib floats
    xs_dt: List[datetime] = _to_datetime_list(xs_raw) if xs_raw else []

    xs_num: List[float] = list(mdates.date2num(xs_dt)) if xs_dt else []

    # Optional smoothing
    ys_s: List[float] = _moving_avg(ys, smooth) if smooth else ys

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = fig.add_subplot(111)

    if xs_num and ys:
        ax.plot(xs_num, ys, linewidth=1.5, label="Score")
        if smooth and ys_s and ys_s is not ys:
            ax.plot(xs_num, ys_s, linestyle="--",
                    linewidth=1.0, label=f"MA({smooth})")
        # Nice date ticks
        locator = mdates.AutoDateLocator()
        formatter = mdates.AutoDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
    else:
        ax.text(0.5, 0.5, "No data", ha="center",
                va="center", transform=ax.transAxes)

    ax.set_title("Threat Score Over Time")
    ax.set_xlabel("Computed At")
    ax.set_ylabel("Score (0..1)")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")

    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
