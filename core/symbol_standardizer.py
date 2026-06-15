"""Course-level symbol standardization before PDF rendering."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict


@dataclass
class CourseSymbolProfile:
    subject_type: str = "engineering"
    phi: str = "φ"
    epsilon: str = "ε"
    epsilon_0: str = "ε₀"
    rho: str = "ρ"
    voltage_ab: str = "Uab"
    enclosed_charge: str = "Q"
    normal_hat: str = "n̂"

    def as_dict(self) -> dict:
        return asdict(self)


def build_course_symbol_profile(course: dict | None = None, chunks: list[dict] | None = None) -> CourseSymbolProfile:
    try:
        from core.subject_type import detect_subject_type

        subject_type = detect_subject_type(course or {})
    except Exception:
        subject_type = "engineering"
    text = "\n".join(str(c.get("text", "")) for c in (chunks or []))
    profile = CourseSymbolProfile(subject_type=subject_type)
    if "UAB" in text:
        profile.voltage_ab = "UAB"
    if "ϕ" in text and "φ" not in text:
        profile.phi = "ϕ"
    return profile


def standardize_symbols(content: str, profile: CourseSymbolProfile | None = None) -> str:
    """Normalize visible PDF content to textbook-like symbols."""
    profile = profile or CourseSymbolProfile()
    text = str(content or "")
    replacements = [
        (r"\bQ_enc\b|Q_\{\\mathrm\{enc\}\}|Q_\{enc\}|Qenc", profile.enclosed_charge),
        (r"\bUAB\b", profile.voltage_ab),
        (r"(?<!\\)\bDelta\s*S\b", "ΔS"),
        (r"(?<!\\)\bepsilon_0\b", profile.epsilon_0),
        (r"(?<!\\)\bepsilon\b", profile.epsilon),
        (r"(?<!\\)\brho_s\b", "ρ_s"),
        (r"(?<!\\)\brho\b", profile.rho),
        (r"(?<!\\)\bvarphi\b|(?<!\\)\bphi\b", profile.phi),
        (r"(?<!\\)\bnabla\b", "∇"),
        (r"\bsqrt\s*\(([^)]+)\)", r"√(\1)"),
        (r"\(a\)/\(D\)", "a/D"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)
    # Outside TeX commands, make common plain powers readable.
    text = re.sub(r"(?<![\\\w])r\^2\b", "r²", text)
    text = re.sub(r"(?<![\\\w])a\^2\b", "a²", text)
    text = re.sub(r"(?<![\\\w])x\^2\b", "x²", text)
    text = re.sub(r"(?<![\\\w])y\^2\b", "y²", text)
    text = re.sub(r"(?<![\\\w])z\^2\b", "z²", text)
    return text


def forbidden_symbol_hits(text: str) -> list[str]:
    tokens = ["Q_enc", "UAB", "(a)/(D)", "r^2", "Delta", "sqrt", "frac", "tag", "quad"]
    return [token for token in tokens if token in str(text or "")]
