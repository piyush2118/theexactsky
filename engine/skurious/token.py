"""Card links that carry their own inputs, so the server stores nothing.

A link like `/s/AAKZ1nAATZoZAA` *is* the birth details. No row is written, no id
is issued, and a card forwarded to a stranger reveals a time and a place but no
name — names are typed on the form and rendered into the picture, never packed
in here. That is the roadmap's "stateless where the plan allows" turned into a
data format, and under the DPDP Act it is the difference between holding
personal data and not.

The packing follows the technical plan: a version byte, four bytes of UTC
minutes per subject, four bytes of place id per subject, a flags byte, and a
CRC-16 so a mistyped link fails loudly instead of drawing the wrong sky.

    one subject  -> 12 bytes -> 16 characters
    two subjects -> 20 bytes -> 28 characters

Minutes are signed and counted from 1900-01-01 UTC, which spans roughly 2185 BCE
to 5985 CE. Ancient skies are a CLI job; the web form takes birthdays.
"""

from __future__ import annotations

import base64
import struct
from dataclasses import dataclass

from .errors import SkuriousError
from .time import Instant

VERSION = 1
EPOCH_JD = 2415020.5                 # 1900-01-01 00:00 UTC
MINUTES_MIN, MINUTES_MAX = -(2 ** 31), 2 ** 31 - 1

# Flag bits. Bits 0 and 1 mark each subject's time as approximate, which is what
# turns on the birth-time uncertainty band. Bit 2 says whether there is a second
# subject at all — the count lives in here rather than in a byte of its own so
# that a two-person card is exactly the 20 bytes the plan budgets for it. The
# top five bits are the rule set, so introducing one later does not invalidate
# every link already forwarded.
FLAG_APPROX_A = 0b0000_0001
FLAG_APPROX_B = 0b0000_0010
FLAG_PAIR = 0b0000_0100
RULESET_SHIFT = 3
RULESET_MAX = 0x1F


@dataclass(frozen=True)
class Subject:
    """One person, or one moment, reduced to the two numbers a link needs."""

    minutes: int                     # UTC minutes since 1900-01-01
    place_id: int                    # GeoNames id
    approximate: bool = False

    @classmethod
    def from_instant(cls, inst: Instant, place, approximate: bool = False
                     ) -> "Subject":
        minutes = round((inst.jd_ut - EPOCH_JD) * 1440.0)
        if not MINUTES_MIN <= minutes <= MINUTES_MAX:
            raise SkuriousError(
                "that date is outside the range a card link can carry "
                "(roughly 2185 BCE to 5985 CE); use the CLI")
        try:
            place_id = int(place.id)
        except (TypeError, ValueError):
            raise SkuriousError(
                f"place {place.id!r} has no GeoNames id, so it cannot go in a "
                f"link; search for the town instead of using coordinates"
            ) from None
        return cls(minutes=minutes, place_id=place_id, approximate=approximate)

    @property
    def jd_ut(self) -> float:
        return EPOCH_JD + self.minutes / 1440.0


def _crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE. Catches the transpositions people make retyping links."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode(subjects: list[Subject], ruleset: int = 0) -> str:
    if not 1 <= len(subjects) <= 2:
        raise SkuriousError("a card carries one or two subjects")
    if not 0 <= ruleset <= RULESET_MAX:
        raise SkuriousError("ruleset id does not fit in five bits")

    flags = ruleset << RULESET_SHIFT
    if subjects[0].approximate:
        flags |= FLAG_APPROX_A
    if len(subjects) > 1:
        flags |= FLAG_PAIR
        if subjects[1].approximate:
            flags |= FLAG_APPROX_B

    body = struct.pack("<B", VERSION)
    for s in subjects:
        body += struct.pack("<iI", s.minutes, s.place_id)
    body += struct.pack("<B", flags)
    body += struct.pack("<H", _crc16(body))
    return base64.urlsafe_b64encode(body).decode("ascii").rstrip("=")


def decode(token: str) -> tuple[list[Subject], int]:
    """Returns the subjects and the rule set id, or raises.

    Every failure here is a link somebody typed wrong or a link somebody
    tampered with. Both must refuse rather than draw a plausible wrong sky.
    """
    padded = token + "=" * (-len(token) % 4)
    try:
        body = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        raise SkuriousError("that link is not a card") from None

    if len(body) not in (12, 20):
        raise SkuriousError("that link is not the right length to be a card")
    payload, checksum = body[:-2], body[-2:]
    if _crc16(payload) != struct.unpack("<H", checksum)[0]:
        raise SkuriousError("that link is damaged — a character is wrong")

    version = payload[0]
    if version != VERSION:
        raise SkuriousError(f"that link was made by version {version} of the card")

    flags = payload[-1]
    count = 2 if flags & FLAG_PAIR else 1
    if len(payload) != 1 + 8 * count + 1:
        raise SkuriousError("that link is malformed")

    subjects = []
    for i in range(count):
        minutes, place_id = struct.unpack("<iI", payload[1 + 8 * i:9 + 8 * i])
        approx = bool(flags & (FLAG_APPROX_A if i == 0 else FLAG_APPROX_B))
        subjects.append(Subject(minutes=minutes, place_id=place_id,
                                approximate=approx))
    return subjects, flags >> RULESET_SHIFT
