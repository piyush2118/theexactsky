#!/usr/bin/env python3
"""Collect objective evidence for the Stage 2 quality rubric.

This script deliberately does *not* ask an LLM to invent a 0-100 score. It runs
mechanical gates that the repository can actually prove and leaves subjective or
human/external gates as UNVERIFIED until evidence exists.

Usage from the repository root:

    python scripts/score-project.py
    python scripts/score-project.py --output /tmp/exactsky-score.json
    python scripts/score-project.py --strict

`--strict` exits non-zero unless every hard gate is PASS. That is appropriate for
a release candidate, not for the normal hill-climb loop while Stage 2 is still
under construction.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
WEB = ROOT / "web"


@dataclass
class Gate:
    id: str
    name: str
    status: str  # PASS | FAIL | UNVERIFIED
    evidence: str
    command: str | None = None


def run(command: Sequence[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def concise(output: str, max_lines: int = 12) -> str:
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def pytest_gate(
    gate_id: str,
    name: str,
    args: Sequence[str],
    *,
    cwd: Path = ENGINE,
    skipped_is_unverified: bool = False,
) -> Gate:
    command = ["uv", "run", "pytest", "-q", *args]
    code, output = run(command, cwd)
    command_text = f"cd {cwd.relative_to(ROOT)} && {' '.join(command)}"

    if code != 0:
        return Gate(gate_id, name, "FAIL", concise(output), command_text)

    if skipped_is_unverified and re.search(r"\bskipped\b|\bSKIPPED\b", output):
        return Gate(
            gate_id,
            name,
            "UNVERIFIED",
            "pytest completed but one or more required checks skipped:\n" + concise(output),
            command_text,
        )

    return Gate(gate_id, name, "PASS", concise(output), command_text)


def g1_science() -> Gate:
    required = [
        ENGINE / "data/_reference/de421.bsp",
        ENGINE / "data/_reference/hip_bright.tsv",
        ENGINE / "data/ephe/sepl_18.se1",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        return Gate(
            "G1",
            "Scientific ephemeris integrity",
            "UNVERIFIED",
            "missing required independent/ephemeris data: " + ", ".join(missing),
            "cd engine && uv run pytest -q tests/test_reference.py -rs",
        )
    return pytest_gate(
        "G1",
        "Scientific ephemeris integrity",
        ["tests/test_reference.py", "-rs"],
        skipped_is_unverified=True,
    )


def g2_time() -> Gate:
    return pytest_gate("G2", "Time/calendar integrity", ["tests/test_time.py"])


def g3_scheme() -> Gate:
    return pytest_gate(
        "G3",
        "Explicit conventions (mechanical portion)",
        ["tests/test_sidereal.py"],
    )


def g4_claims() -> Gate:
    return pytest_gate("G4", "Claim epistemic integrity", ["tests/test_claims.py"])


def g5_render() -> Gate:
    if shutil.which("resvg") is None:
        return Gate(
            "G5",
            "Deterministic/render integrity",
            "UNVERIFIED",
            "resvg is not installed, so raster/Indic/golden checks cannot be treated as verified",
            "cd engine && uv run pytest -q tests/test_render.py -rs",
        )
    return pytest_gate(
        "G5",
        "Deterministic/render integrity",
        ["tests/test_render.py", "-rs"],
        skipped_is_unverified=True,
    )


def g6_privacy() -> Gate:
    engine_gate = pytest_gate(
        "G6",
        "Privacy/statelessness",
        ["tests/test_token.py"],
    )
    if engine_gate.status != "PASS":
        return engine_gate

    web_gate = pytest_gate(
        "G6",
        "Privacy/statelessness",
        [],
        cwd=WEB,
    )
    if web_gate.status != "PASS":
        return web_gate

    return Gate(
        "G6",
        "Privacy/statelessness",
        "PASS",
        "token tests and full web route/privacy tests passed",
        "cd engine && uv run pytest -q tests/test_token.py; cd ../web && uv run pytest -q",
    )


def g7_architecture() -> Gate:
    offenders: list[str] = []
    for path in sorted(WEB.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"(^|\n)\s*(import\s+swisseph|from\s+swisseph\s+import)", text):
            offenders.append(str(path.relative_to(ROOT)))

    if offenders:
        return Gate(
            "G7",
            "Single computation core",
            "FAIL",
            "web imports Swiss Ephemeris directly: " + ", ".join(offenders),
        )

    return Gate(
        "G7",
        "Single computation core",
        "UNVERIFIED",
        "static scan found no direct swisseph import in web/, but release still requires architecture review for duplicated astronomy/sidereal arithmetic",
    )


def g8_licensing() -> Gate:
    license_file = ROOT / "LICENSE"
    engine_toml = ENGINE / "pyproject.toml"
    web_toml = WEB / "pyproject.toml"
    missing = [
        str(p.relative_to(ROOT))
        for p in (license_file, engine_toml, web_toml)
        if not p.exists()
    ]
    if missing:
        return Gate(
            "G8",
            "Licensing/data provenance",
            "FAIL",
            "missing licensing/project metadata: " + ", ".join(missing),
        )

    project_text = engine_toml.read_text(encoding="utf-8") + web_toml.read_text(encoding="utf-8")
    if "AGPL-3.0-or-later" not in project_text:
        return Gate(
            "G8",
            "Licensing/data provenance",
            "FAIL",
            "engine/web project metadata no longer consistently declares AGPL-3.0-or-later",
        )

    return Gate(
        "G8",
        "Licensing/data provenance",
        "UNVERIFIED",
        "expected AGPL metadata is present; release still requires review of newly introduced dependencies/data and their redistribution terms",
    )


def g9_jyotish_reconciliation() -> Gate:
    candidates = [
        ENGINE / "tests/fixtures/kuta_reconciliation.tsv",
        ENGINE / "tests/fixtures/jyotish_reconciliation.tsv",
    ]
    present = [str(p.relative_to(ROOT)) for p in candidates if p.exists()]
    return Gate(
        "G9",
        "Jyotish reconciliation",
        "UNVERIFIED",
        (
            "reconciliation artifacts present for inspection: " + ", ".join(present)
            if present
            else "no completed Stage 2 two-program/20-pair reconciliation artifact detected"
        )
        + "; this gate must be promoted manually only after both independent Jyotish references were actually compared",
    )


def g10_integrated_release() -> Gate:
    return Gate(
        "G10",
        "Integrated release CI",
        "UNVERIFIED",
        "local scorer cannot establish GitHub release-candidate CI status; verify the exact candidate commit in GitHub Actions",
        "bash scripts/check-full.sh && verify GitHub Actions on the same commit",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero unless all hard gates are PASS",
    )
    args = parser.parse_args()

    gates = [
        g1_science(),
        g2_time(),
        g3_scheme(),
        g4_claims(),
        g5_render(),
        g6_privacy(),
        g7_architecture(),
        g8_licensing(),
        g9_jyotish_reconciliation(),
        g10_integrated_release(),
    ]

    summary = {status: sum(g.status == status for g in gates) for status in ("PASS", "FAIL", "UNVERIFIED")}
    payload = {
        "project": "theexactsky",
        "milestone": "stage-2-forwardable-compatibility-card",
        "hard_gates": [asdict(g) for g in gates],
        "summary": summary,
        "weighted_quality_score": None,
        "weighted_score_note": (
            "Not auto-generated. Score the 0-4 domains in QUALITY_SCORE.md from this machine evidence plus "
            "product/browser/provenance/reconciliation review."
        ),
    }

    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    if summary["FAIL"]:
        return 1
    if args.strict and summary["UNVERIFIED"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
