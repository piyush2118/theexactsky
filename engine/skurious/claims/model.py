"""The claim DSL: a dating proposal written down so a machine can check it.

A claim is somebody's published argument that an event happened on a particular
date, expressed as constraints on the sky. Loading one does not endorse it. The
evaluator reports what each constraint asks for and what the sky actually did,
and stops there — no verdict, no score, no adjudication. The renders do the
arguing, and a reader who disagrees can change the scheme and re-run it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..errors import ClaimError
from ..sidereal import Scheme

CONSTRAINT_TYPES = {
    "planet_in_nakshatra", "retrograde", "eclipse_pair", "conjunction",
}


@dataclass(frozen=True)
class Event:
    """A named moment in the claim. `time` may be a clock time or 'sunrise'."""

    name: str
    date: str
    time: str = "sunrise"

    @property
    def stated_time(self) -> str:
        return self.time


@dataclass(frozen=True)
class Constraint:
    id: str
    type: str
    at: str                      # which event
    params: dict

    def require(self, key: str):
        if key not in self.params:
            raise ClaimError(
                f"constraint {self.id} ({self.type}) needs a {key!r}")
        return self.params[key]


@dataclass(frozen=True)
class Claim:
    id: str
    source: str
    calendar: str
    scheme: Scheme
    observer: str
    events: dict[str, Event]
    constraints: list[Constraint]
    title: str = ""
    note: str = ""
    # Whether a human has checked the source against the primary publication.
    # The plate prints this, because a plate that silently mixes a verified
    # citation with a guessed one is worse than no plate.
    citation_status: str = "unverified"
    date_status: str = "placeholder"
    path: Path | None = None

    def event(self, name: str) -> Event:
        try:
            return self.events[name]
        except KeyError:
            raise ClaimError(
                f"claim {self.id} has no event {name!r}; "
                f"it has {', '.join(sorted(self.events))}") from None

    def with_scheme(self, scheme: Scheme) -> "Claim":
        """Re-run the same argument under a different ayanamsa.

        This is the whole answer to "scholars disagree about the ayanamsa": you
        do not pick a side, you show the table under each one.
        """
        return Claim(id=self.id, source=self.source, calendar=self.calendar,
                     scheme=scheme, observer=self.observer, events=self.events,
                     constraints=self.constraints, title=self.title,
                     note=self.note, citation_status=self.citation_status,
                     date_status=self.date_status, path=self.path)


@dataclass(frozen=True)
class ConstraintResult:
    id: str
    type: str
    passes: bool
    stated: str                  # what the claim asked for, in words
    computed: str                # what the sky did, in words
    evidence: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ClaimResult:
    claim: Claim
    scheme: Scheme
    results: list[ConstraintResult]
    instants: dict[str, object]  # event name -> Instant

    @property
    def passed(self) -> int:
        return sum(r.passes for r in self.results)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def summary(self) -> str:
        """Counts, not a verdict. '3 of 4 constraints met' is a fact."""
        return f"{self.passed} of {self.total} constraints met"


def _parse_scheme(raw: dict | None, calendar: str) -> Scheme:
    raw = dict(raw or {})
    raw.setdefault("calendar", calendar)
    return Scheme(**raw)


def load(path: Path) -> Claim:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ClaimError(f"{path} is not a claim document")

    for key in ("id", "source", "observer", "events", "constraints"):
        if key not in doc:
            raise ClaimError(f"{path} is missing {key!r}")

    calendar = doc.get("calendar", "auto")
    events = {}
    for name, entry in doc["events"].items():
        if isinstance(entry, str):
            entry = {"date": entry}
        events[name] = Event(name=name, date=str(entry["date"]),
                             time=str(entry.get("time", "sunrise")))

    constraints = []
    for raw in doc["constraints"]:
        params = dict(raw)
        cid = params.pop("id", None)
        ctype = params.pop("type", None)
        at = params.pop("at", None) or params.pop("within_days_of", None)
        if cid is None or ctype is None:
            raise ClaimError(f"{path}: every constraint needs an id and a type")
        if ctype not in CONSTRAINT_TYPES:
            raise ClaimError(
                f"{path}: constraint {cid} has type {ctype!r}, which this "
                f"version does not implement; have "
                f"{', '.join(sorted(CONSTRAINT_TYPES))}")
        if at is None:
            raise ClaimError(f"{path}: constraint {cid} does not say when")
        if ctype in ("eclipse_pair", "conjunction"):
            params.setdefault("within_days_of", at)
        constraints.append(Constraint(id=str(cid), type=ctype, at=str(at),
                                      params=params))

    return Claim(
        id=str(doc["id"]),
        source=str(doc["source"]),
        calendar=calendar,
        scheme=_parse_scheme(doc.get("scheme"), calendar),
        observer=str(doc["observer"]),
        events=events,
        constraints=constraints,
        title=str(doc.get("title", doc["id"])),
        note=str(doc.get("note", "")),
        citation_status=str(doc.get("citation_status", "unverified")),
        date_status=str(doc.get("date_status", "placeholder")),
        path=Path(path),
    )


def load_dir(directory: Path) -> list[Claim]:
    """Every claim in a directory, in filename order so plates are stable."""
    return [load(p) for p in sorted(Path(directory).glob("*.yaml"))]
