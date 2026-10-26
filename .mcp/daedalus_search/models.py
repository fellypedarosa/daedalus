"""Stable internal and serialized retrieval contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256

SCHEMA_VERSION = 1
PARSER_VERSION = 4
ADMIN_FILES = {"index.md", "log.md", "Ingestion_Tracker.md"}


def digest(value: str | bytes) -> str:
    return sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


@dataclass
class Passage:
    id: str
    path: str
    section: str
    start_line: int
    end_line: int
    text: str
    hash: str
    start_offset: int = 0
    end_offset: int = 0


@dataclass
class Relation:
    source: str
    reference: str
    kind: str
    line: int
    target: str | None = None
    status: str = "unresolved"
    candidates: list[str] = field(default_factory=list)


@dataclass
class Document:
    path: str
    layer: str
    title: str
    domain: str
    hash: str
    text: str
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    has_frontmatter: bool = False
    passages: list[Passage] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)


@dataclass
class Candidate:
    passage: Passage
    score: float = 0.0
    channels: set[str] = field(default_factory=set)
    via: list[dict] = field(default_factory=list)


class SearchUnavailable(RuntimeError):
    """The service must report failure rather than an empty successful search."""


class AmbiguousReference(ValueError):
    def __init__(self, reference: str, candidates: list[str]):
        self.candidates = candidates
        super().__init__(f"Ambiguous reference {reference!r}: {', '.join(candidates)}")
