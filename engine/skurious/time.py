"""Local date, time and place to an `Instant`.

The whole engine hangs off this module: everything downstream takes an
`Instant` and never re-derives a Julian day. Three things are explicit here that
are usually hidden defaults, and each of them has moved somebody's chart:

* which **calendar** the written date is in (Julian before 1582-10-15);
* which **time scale** turned the wall clock into UTC (a named zone, or Local
  Mean Time for dates before zones existed);
* how uncertain **ΔT** is, which for ancient dates decides what was rising.

Years use astronomical numbering internally: 1 BCE is year 0, 3067 BCE is
-3066. Outputs print both forms, because a claim paper says "3067 BCE" and a
Julian-day routine wants -3066.
"""

from __future__ import annotations

import functools
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe
import yaml

from .errors import (AmbiguousLocalTime, NonexistentLocalTime,
                     OutOfEphemerisRange, SkuriousError)
from .paths import RULES
from .swiss import init_ephemeris

# The Gregorian reform: 1582-10-04 Julian was followed by 1582-10-15 Gregorian.
GREGORIAN_START = (1582, 10, 15)

# What the vendored .se1 files cover.
EPHEMERIS_RANGE = (-6000, 2400)

DATE_RE = re.compile(r"^(?P<year>-?\d{1,6})-(?P<month>\d{1,2})-(?P<day>\d{1,2})$")
TIME_RE = re.compile(r"^(?P<h>\d{1,2}):(?P<m>\d{2})(?::(?P<s>\d{2}(?:\.\d+)?))?$")


@dataclass(frozen=True)
class Instant:
    """One moment, fully described, with the choices that produced it."""

    jd_ut: float
    jd_tt: float
    delta_t: float                 # seconds
    delta_t_sigma: float           # seconds, 1σ
    delta_t_extrapolated: bool
    calendar: str                  # "gregorian" | "julian"
    timescale: str                 # "zone" | "lmt"
    utc_offset: float              # hours east of Greenwich
    tz_label: str                  # "America/New_York EST" or "LMT +05:32"
    source_local_iso: str          # exactly what the user typed, normalised

    @property
    def year(self) -> int:
        return swe.revjul(self.jd_ut, cal_flag(self.calendar))[0]

    @property
    def show_sigma(self) -> bool:
        return self.year <= _sigma_table()["print_sigma_before"]

    def with_offset_minutes(self, minutes: float) -> "Instant":
        """The same instant shifted, for birth-time sweeps and window scans."""
        jd = self.jd_ut + minutes / 1440.0
        return _build(jd, self.calendar, self.timescale, self.utc_offset,
                      self.tz_label, self.source_local_iso)


# --------------------------------------------------------------------------
# calendars and year numbering
# --------------------------------------------------------------------------

def cal_flag(calendar: str) -> int:
    if calendar == "gregorian":
        return swe.GREG_CAL
    if calendar == "julian":
        return swe.JUL_CAL
    raise SkuriousError(f"unknown calendar {calendar!r}")


def resolve_calendar(calendar: str, y: int, m: int, d: int) -> str:
    """"auto" means the calendar actually in use on that date."""
    if calendar in ("gregorian", "julian"):
        return calendar
    if calendar != "auto":
        raise SkuriousError(f"unknown calendar {calendar!r}")
    return "gregorian" if (y, m, d) >= GREGORIAN_START else "julian"


def era_year(astronomical_year: int) -> str:
    """-3066 -> '3067 BCE'; 1994 -> '1994 CE'. The form a reader expects."""
    if astronomical_year > 0:
        return f"{astronomical_year} CE"
    return f"{1 - astronomical_year} BCE"


def both_year_forms(astronomical_year: int) -> str:
    """'3067 BCE (astronomical -3066)', which is what ancient renders print."""
    if astronomical_year > 0:
        return era_year(astronomical_year)
    return f"{era_year(astronomical_year)} (astronomical {astronomical_year})"


def parse_date(text: str) -> tuple[int, int, int]:
    """'2019-02-14' or '-3066-11-22'. The year is astronomical, not an era."""
    m = DATE_RE.match(text.strip())
    if not m:
        raise SkuriousError(
            f"cannot read date {text!r}; expected YYYY-MM-DD "
            f"with an astronomical year (3067 BCE is -3066)")
    return int(m["year"]), int(m["month"]), int(m["day"])


def parse_time(text: str) -> float:
    """'19:30' or '19:30:45' to hours. Named times are resolved by callers."""
    m = TIME_RE.match(text.strip())
    if not m:
        raise SkuriousError(f"cannot read time {text!r}; expected HH:MM")
    h, mi = int(m["h"]), int(m["m"])
    s = float(m["s"] or 0.0)
    if not (0 <= h < 24 and 0 <= mi < 60 and 0 <= s < 60):
        raise SkuriousError(f"time {text!r} is out of range")
    return h + mi / 60 + s / 3600


# --------------------------------------------------------------------------
# ΔT
# --------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _sigma_table() -> dict:
    doc = yaml.safe_load((RULES / "deltat_sigma.yaml").read_text())
    doc["_years"] = sorted(doc["sigma_seconds"])
    return doc


def delta_t_sigma(year: int) -> tuple[float, bool]:
    """1σ of ΔT in seconds, and whether the value is extrapolated guesswork."""
    table = _sigma_table()
    years, sig = table["_years"], table["sigma_seconds"]
    extrapolated = year < table["extrapolated_before"]
    if year <= years[0]:
        return float(sig[years[0]]), extrapolated
    if year >= years[-1]:
        return float(sig[years[-1]]), extrapolated
    for lo, hi in zip(years, years[1:]):
        if lo <= year <= hi:
            t = (year - lo) / (hi - lo)
            return float(sig[lo] + t * (sig[hi] - sig[lo])), extrapolated
    raise SkuriousError("unreachable: ΔT σ table is not sorted")


# --------------------------------------------------------------------------
# building an Instant
# --------------------------------------------------------------------------

def _build(jd_ut: float, calendar: str, timescale: str, offset: float,
           tz_label: str, source: str) -> Instant:
    year = swe.revjul(jd_ut, cal_flag(calendar))[0]
    lo, hi = EPHEMERIS_RANGE
    if not lo <= year <= hi:
        raise OutOfEphemerisRange(
            f"year {era_year(year)} is outside the vendored ephemeris "
            f"({era_year(lo)} to {era_year(hi)})")
    # `swe.deltat_ex` depends on Swiss's process-global ephemeris path just like
    # body calculations do. Initialize it here so a fresh process can construct
    # an Instant without relying on some earlier ephem call/test to set state.
    init_ephemeris()
    dt_seconds = swe.deltat_ex(jd_ut, swe.FLG_SWIEPH) * 86400.0
    sigma, extrapolated = delta_t_sigma(year)
    return Instant(
        jd_ut=jd_ut,
        jd_tt=jd_ut + dt_seconds / 86400.0,
        delta_t=dt_seconds,
        delta_t_sigma=sigma,
        delta_t_extrapolated=extrapolated,
        calendar=calendar,
        timescale=timescale,
        utc_offset=offset,
        tz_label=tz_label,
        source_local_iso=source,
    )


def _zone_offset(tz: str, y: int, m: int, d: int, hour: float) -> tuple[float, str]:
    """UTC offset in hours for a wall-clock time in a named zone.

    Raises on the two wall-clock times that are not a single instant: the hour
    an autumn fold repeats, and the hour a spring jump never has.
    """
    try:
        zone = ZoneInfo(tz)
    except ZoneInfoNotFoundError as exc:
        raise SkuriousError(f"unknown timezone {tz!r}") from exc

    whole = int(hour)
    minute = int(round((hour - whole) * 3600))
    naive = datetime(y, m, d, whole) + timedelta(seconds=minute)

    early = naive.replace(tzinfo=zone, fold=0)
    late = naive.replace(tzinfo=zone, fold=1)

    # Order matters. In *both* a spring gap and an autumn fold the two `fold`
    # values give different offsets, so the offsets alone cannot tell the two
    # apart. Only the round trip can: a wall time in a gap does not survive it,
    # and a repeated wall time does.
    roundtrip = early.astimezone(timezone.utc).astimezone(zone)
    if roundtrip.replace(tzinfo=None) != naive:
        raise NonexistentLocalTime(
            f"{naive.isoformat()} does not exist in {tz}; the clock jumps from "
            f"{naive.strftime('%H:%M')} forward and never reads it")

    if early.utcoffset() != late.utcoffset():
        raise AmbiguousLocalTime(
            f"{naive.isoformat()} happens twice in {tz} "
            f"(offsets {early.utcoffset()} and {late.utcoffset()}); "
            f"say which one, or give the time as UTC")

    offset = early.utcoffset()
    assert offset is not None
    hours = offset.total_seconds() / 3600.0
    return hours, f"{tz} {early.tzname()}"


def _lmt_offset(lon: float) -> tuple[float, str]:
    """Local Mean Time: the offset the Sun itself gives, before zones existed."""
    hours = lon / 15.0
    sign = "+" if hours >= 0 else "-"
    total = abs(hours) * 60
    return hours, f"LMT {sign}{int(total // 60):02d}:{int(round(total % 60)):02d}"


def instant(date: str, time: str, place, *, calendar: str = "auto",
            timescale: str = "zone") -> Instant:
    """The one constructor. `place` is anything with `.lat`, `.lon`, `.tz`."""
    y, mo, d = parse_date(date)
    hour = parse_time(time)
    cal = resolve_calendar(calendar, y, mo, d)

    if timescale not in ("zone", "lmt"):
        raise SkuriousError(f"unknown timescale {timescale!r}")

    # Named zones only exist from the 1880s, and zoneinfo cannot represent a
    # year below 1 at all. Before that the only defensible clock is the Sun.
    use_lmt = timescale == "lmt" or place.tz in ("", "LMT") or y < 1
    if use_lmt:
        offset, label = _lmt_offset(place.lon)
        scale = "lmt"
    else:
        offset, label = _zone_offset(place.tz, y, mo, d, hour)
        scale = "zone"

    jd_ut = swe.julday(y, mo, d, 0.0, cal_flag(cal)) + (hour - offset) / 24.0
    source = f"{date}T{_fmt_hour(hour)}"
    return _build(jd_ut, cal, scale, offset, label, source)


def instant_from_jd(jd_ut: float, place, *, calendar: str = "auto",
                    timescale: str = "zone") -> Instant:
    """Wrap a Julian day found by a search (an eclipse, a conjunction minimum)."""
    probe_year = swe.revjul(jd_ut, swe.GREG_CAL)[0]
    cal = resolve_calendar(calendar, *swe.revjul(jd_ut, swe.GREG_CAL)[:3])
    use_lmt = timescale == "lmt" or place.tz in ("", "LMT") or probe_year < 1
    if use_lmt:
        offset, label = _lmt_offset(place.lon)
        scale = "lmt"
    else:
        y, mo, d, h = swe.revjul(jd_ut + 0.5, cal_flag(cal))  # rough local date
        offset, label = _zone_offset(place.tz, y, mo, d, 12.0)
        scale = "zone"
    y, mo, d, h = swe.revjul(jd_ut + offset / 24.0, cal_flag(cal))
    source = f"{y:05d}-{mo:02d}-{d:02d}T{_fmt_hour(h)}"
    return _build(jd_ut, cal, scale, offset, label, source)


def local_parts(inst: Instant) -> tuple[int, int, int, float]:
    """Calendar date and fractional hour in the instant's own local scale."""
    return swe.revjul(inst.jd_ut + inst.utc_offset / 24.0, cal_flag(inst.calendar))


def _fmt_hour(hour: float) -> str:
    total = round(hour * 3600)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}" if s == 0 else f"{h:02d}:{m:02d}:{s:02d}"


def format_local(inst: Instant) -> str:
    """'14 February 2019, 19:30' — the line printed under a render."""
    y, mo, d, h = local_parts(inst)
    return f"{d} {MONTHS[mo - 1]} {both_year_forms(y)}, {_fmt_hour(h)}"


def scheme_footer(inst: Instant, scheme) -> str:
    """The line that makes a render reproducible: every choice, spelled out."""
    bits = [scheme.ayanamsa_label, f"{scheme.nakshatra_boundaries} nakshatras",
            inst.calendar.capitalize(), inst.tz_label]
    if inst.show_sigma:
        sigma = inst.delta_t_sigma
        mark = "~" if inst.delta_t_extrapolated else "±"
        bits.append(f"ΔT {inst.delta_t / 60:.0f} min {mark}{sigma / 60:.0f} min")
    return " · ".join(bits)


MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def julian_centuries(inst: Instant) -> float:
    return (inst.jd_tt - 2451545.0) / 36525.0


def hours_to_hms(hour: float) -> tuple[int, int, int]:
    total = int(round(hour * 3600)) % 86400
    return total // 3600, (total % 3600) // 60, total % 60


def deg_to_dms(deg: float) -> tuple[int, int, float]:
    sign = -1 if deg < 0 else 1
    deg = abs(deg)
    d = int(deg)
    rem = (deg - d) * 60
    m = int(rem)
    s = (rem - m) * 60
    return sign * d, m, s


def format_dms(deg: float, positive: str, negative: str) -> str:
    """Coordinates as they appear under a print: 40°31′N."""
    d, m, _ = deg_to_dms(abs(deg))
    hemisphere = positive if deg >= 0 else negative
    return f"{d}°{m:02d}′{hemisphere}"


def wrap360(deg: float) -> float:
    return deg % 360.0


def angular_sep(lon_a: float, lat_a: float, lon_b: float, lat_b: float) -> float:
    """Great-circle separation in degrees, for conjunction searches."""
    la, lb = math.radians(lat_a), math.radians(lat_b)
    dl = math.radians(lon_a - lon_b)
    cos_d = math.sin(la) * math.sin(lb) + math.cos(la) * math.cos(lb) * math.cos(dl)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_d))))
