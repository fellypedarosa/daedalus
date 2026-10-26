"""Credential heuristics shared by ingestion and repository tests."""
from __future__ import annotations
import re
import json

def _patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    prefixes = ("gh" + "p_", "gh" + "o_", "gl" + "pat-", "xox" + "b-")
    return (
        ("PRIVATE_KEY", re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"
        )),
        ("PROVIDER_TOKEN", re.compile(
            r"(?:" + "|".join(map(re.escape, prefixes)) + r")[A-Za-z0-9_-]{20,}"
        )),
        ("AWS_ACCESS_KEY_ID", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
        ("DAEDALUS_TOKEN", re.compile(r"daedalus_sec_[0-9a-fA-F]{64}\b")),
    )


PATTERNS = _patterns()
ALLOW_MARKER = re.compile(
    r'^\s*(?:#\s*|<!--\s*)daedalus-scan: allow ([A-Z_]+) '
    r'value=("(?:[^"\\]|\\.)*") reason=("(?:[^"\\]|\\.)*")\s*(?:-->)?\s*$'
)
MARKER_START = re.compile(r'^\s*(?:#\s*|<!--\s*)daedalus-scan:')
ASSIGNMENT = re.compile(
    r'''(?ix)(?<![\w])(?:[a-z0-9]+_)*
    (?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd|secret|token)
    ["']?\s*(?::|=(?!=))\s*
    (?:"([^"\r\n]*)"|'([^'\r\n]*)'|
    (\$\{\{.*?\}\}|\$\{[^}]+\}|[^\s,;\x23`]+))'''
)


def _is_placeholder(value: str) -> bool:
    """Allow explicit examples and variable references, not arbitrary punctuation."""
    normalized = value.lower()
    return (
        not value
        or re.fullmatch(r"\$\{\{.*\}\}|\$\{[^}]+\}|\$[A-Za-z_]\w*|<[^>]+>", value) is not None
        or normalized in {"changeme", "change-me", "example", "placeholder"}
        or normalized.startswith(("your_", "your-", "replace_me", "replace-this", "replace-with"))
        or normalized.startswith("daedalus_sec_replace_")
        or normalized == "daedalus_sec_another_example_token_replace"
    )


def _scan_text(text: str, *, source_code: bool = False) -> list[tuple[int, str]]:
    findings = []
    pending = None
    for number, line in enumerate(text.splitlines(), start=1):
        allowance, pending = pending, None
        if MARKER_START.match(line):
            marker = ALLOW_MARKER.fullmatch(line)
            try:
                if marker is None:
                    raise ValueError("Malformed marker")
                rule, value, reason = marker.groups()
                value, reason = json.loads(value), json.loads(reason)
                if (rule not in {name for name, _ in PATTERNS} | {"CREDENTIAL_ASSIGNMENT"}
                        or not value or not reason.strip()
                        or line.lstrip().startswith("<!--") != line.rstrip().endswith("-->")):
                    raise ValueError("Invalid marker")
                pending = (rule, value)
                continue
            except (ValueError, TypeError):
                findings.append((number, "INVALID_ALLOW_MARKER"))

        def report(rule: str, value: str) -> None:
            nonlocal allowance
            if allowance == (rule, value):
                allowance = None  # Exempt one exact match on this line only.
            else:
                findings.append((number, rule))

        for rule, pattern in PATTERNS:
            for match in pattern.finditer(line):
                report(rule, match.group())
        for match in ASSIGNMENT.finditer(line):
            quoted = match.group(1) is not None or match.group(2) is not None
            value = next(group for group in match.groups() if group is not None)
            # In source code, inspect string literals rather than expressions.
            # Provider patterns above still inspect every line in full.
            if source_code and (not quoted or line[match.end():].lstrip().startswith("+")):
                continue
            if not quoted and re.match(r"^[A-Za-z_]\w*(?:\.\w+)*(?:\(|\[)", value):
                continue
            if len(value) >= 8 and not _is_placeholder(value):
                report("CREDENTIAL_ASSIGNMENT", value)
    return findings
