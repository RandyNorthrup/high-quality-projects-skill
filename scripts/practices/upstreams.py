"""Hold every pinned upstream version in one file, fail when it goes stale, and watch releases.

Lockfiles and update bots cover package ecosystems. CLIs downloaded in CI,
protocol and API versions, and snapshots have no bot,
so they rot silently. upstreams.json names each one, where it is pinned, where
its releases are watched, and when a person last reviewed it.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from .masking import mask
from .model import Finding, PracticeInputError
from .source import dialect_of, language_of, python_comments, read_text

if TYPE_CHECKING:
    from collections.abc import Mapping

SCHEMA_VERSION = 1
KINDS = frozenset(
    {"runtime", "sdk", "cli", "tool", "action", "protocol", "api", "snapshot", "service"}
)
ENTRY_FIELDS = frozenset(
    {
        "name",
        "kind",
        "pinned",
        "used_in",
        "watch",
        "reviewed",
        "latest_seen",
        "max_age_days",
        "hold",
    }
)
GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
# The REST API version this watch speaks. Listed in upstreams.json, so a new
# GitHub API version is reviewed like any other upstream change.
GITHUB_API_VERSION = "2026-03-10"
# A '#' comment in YAML, TOML, INI, shell, PowerShell, Dockerfiles, and
# requirements files starts a line or follows whitespace.
HASH_COMMENT = re.compile(r"(?:^|(?<=\s))#.*$", re.MULTILINE)
GITHUB_RELEASE_URL = "https://api.github.com/repos/{repository}/releases/latest"
USER_AGENT = "high-quality-projects-skill-verify-practices"


@dataclass(frozen=True)
class Hold:
    """A recorded decision to stay behind an upstream release until a date."""

    reason: str
    until: date


@dataclass(frozen=True)
class Upstream:
    """One pinned upstream and how it is kept current."""

    name: str
    pinned: str
    used_in: tuple[str, ...]
    watch_type: str
    watch_target: str
    reviewed: date
    latest_seen: str
    max_age_days: int
    hold: Hold | None


def fail(location: str, message: str) -> NoReturn:
    """Raise an input error naming where upstreams.json is malformed."""
    error = f"upstreams.json {location}: {message}"
    raise PracticeInputError(error)


def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Refuse duplicate JSON keys, which would silently drop an entry."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            message = f"duplicate key {key!r}"
            raise PracticeInputError(message)
        result[key] = value
    return result


def load_json(path: Path, label: str) -> object:
    """Parse a JSON document strictly, reporting any failure as an input error."""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=reject_duplicates)
    except (OSError, UnicodeError, ValueError) as error:
        message = f"{label} cannot be read as JSON: {error}"
        raise PracticeInputError(message) from error


def text_field(entry: Mapping[str, object], key: str, location: str) -> str:
    """Return a required non-empty string field."""
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(location, f"{key} must be a non-empty string")
    return value


def date_field(value: object, location: str, key: str) -> date:
    """Parse an ISO date that is not in the future."""
    try:
        parsed = date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        parsed = None
    if parsed is None:
        fail(location, f"{key} must be an ISO date (YYYY-MM-DD)")
    return parsed


def watch_of(value: object, location: str) -> tuple[str, str]:
    """Validate the release source for one upstream."""
    if not isinstance(value, dict):
        fail(location, "watch must be an object")
    kind = value.get("type")
    if kind == "github-releases" and set(value) == {"type", "repository"}:
        repository = value["repository"]
        if isinstance(repository, str) and GITHUB_REPOSITORY.match(repository):
            return kind, repository
    if kind == "manual" and set(value) == {"type", "url"}:
        url = value["url"]
        if isinstance(url, str) and url.startswith("https://"):
            return kind, url
    message = (
        'watch must be {"type": "github-releases", "repository": "owner/name"} '
        'or {"type": "manual", "url": "https://..."}'
    )
    fail(location, message)


def hold_of(value: object, location: str) -> Hold | None:
    """Validate an optional decision to stay behind the latest release."""
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"reason", "until"}:
        fail(location, 'hold must be null or {"reason": ..., "until": "YYYY-MM-DD"}')
    return Hold(
        text_field(value, "reason", location), date_field(value["until"], location, "until")
    )


def upstream_of(entry: object, index: int, today: date) -> Upstream:
    """Validate one upstream entry."""
    location = f"upstreams[{index}]"
    if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
        fail(location, f"fields must be exactly {', '.join(sorted(ENTRY_FIELDS))}")
    name = text_field(entry, "name", location)
    if entry["kind"] not in KINDS:
        fail(location, f"kind must be one of {', '.join(sorted(KINDS))}")
    used_in = entry["used_in"]
    if not isinstance(used_in, list) or not used_in or not all(isinstance(p, str) for p in used_in):
        fail(location, "used_in must list the files where the pin is written")
    max_age = entry["max_age_days"]
    if not isinstance(max_age, int) or isinstance(max_age, bool) or max_age < 1:
        fail(location, "max_age_days must be a positive integer")
    reviewed = date_field(entry["reviewed"], location, "reviewed")
    if reviewed > today:
        fail(location, "reviewed is in the future")
    watch_type, watch_target = watch_of(entry["watch"], location)
    return Upstream(
        name,
        text_field(entry, "pinned", location),
        tuple(used_in),
        watch_type,
        watch_target,
        reviewed,
        text_field(entry, "latest_seen", location),
        max_age,
        hold_of(entry["hold"], location),
    )


def load_upstreams(path: Path, today: date) -> list[Upstream]:
    """Load and validate upstreams.json."""
    data = load_json(path, "upstreams.json")
    if not isinstance(data, dict) or set(data) != {"schema_version", "upstreams"}:
        fail("root", 'fields must be exactly "schema_version" and "upstreams"')
    if data["schema_version"] != SCHEMA_VERSION:
        fail("schema_version", f"expected {SCHEMA_VERSION}")
    entries = data["upstreams"]
    if not isinstance(entries, list):
        fail("upstreams", "must be a list")
    upstreams = [upstream_of(entry, index, today) for index, entry in enumerate(entries)]
    names = [item.name for item in upstreams]
    if len(names) != len(set(names)):
        fail("upstreams", "names must be unique")
    return upstreams


def today_utc() -> date:
    """Return the current UTC date from the real clock."""
    return datetime.now(tz=UTC).date()


def staleness_findings(
    root: Path, relative: str, upstreams: list[Upstream], today: date
) -> list[Finding]:
    """Fail when a pin drifted, a review lapsed, or the project fell behind without a hold."""
    findings = []
    for item in upstreams:
        age = (today - item.reviewed).days
        if age > item.max_age_days:
            message = (
                f"{item.name} was last reviewed {age} days ago (allowed {item.max_age_days}); "
                "check its releases and changelog, then update reviewed"
            )
            findings.append(Finding(relative, 1, "upstream-review-overdue", message))
        if item.hold and item.hold.until < today:
            message = (
                f"{item.name} hold expired on {item.hold.until.isoformat()}: {item.hold.reason}"
            )
            findings.append(Finding(relative, 1, "upstream-hold-expired", message))
        elif item.latest_seen.removeprefix("v") != item.pinned.removeprefix("v") and not item.hold:
            message = (
                f"{item.name} is pinned at {item.pinned} but {item.latest_seen} is released; "
                "incorporate it, or record a hold with a reason and an end date"
            )
            findings.append(Finding(relative, 1, "upstream-behind", message))
        for used in item.used_in:
            target = root / used
            if not target.is_file() or not pin_written(read_text(target), used, item.pinned):
                message = (
                    f"{item.name} pin {item.pinned} is not written as a version in the code "
                    f"of {used}"
                )
                findings.append(Finding(relative, 1, "upstream-pin-drift", message))
    return findings


def code_without_comments(text: str, relative: str) -> str:
    """Remove comments so a version kept only in a note never counts as the pin."""
    suffix = Path(relative).suffix.lower()
    if suffix == ".json":
        return text
    if suffix == ".py":
        lines = text.splitlines()
        for number, comment in python_comments(text):
            lines[number - 1] = lines[number - 1].removesuffix(comment)
        return "\n".join(lines)
    language = language_of(Path(relative))
    if language and language not in {"powershell", "shell"}:
        return mask(text, dialect_of(language)).code
    return HASH_COMMENT.sub("", text)


def pin_written(text: str, relative: str, pinned: str) -> bool:
    """Report the pin written as a whole version token outside comments."""
    pattern = rf"(?<![\w.])v?{re.escape(pinned.removeprefix('v'))}(?![\w.])"
    return re.search(pattern, code_without_comments(text, relative)) is not None


def release_version(body: bytes) -> str:
    """Return the tag of a GitHub 'latest release' response, without a leading v."""
    try:
        data = json.loads(body)
    except ValueError as error:
        message = f"release response is not JSON: {error}"
        raise PracticeInputError(message) from error
    tag = data.get("tag_name") if isinstance(data, dict) else None
    if not isinstance(tag, str) or not tag:
        message = "release response has no tag_name"
        raise PracticeInputError(message)
    return tag.removeprefix("v")


def fetch(url: str, timeout: float) -> bytes:
    """GET a GitHub API URL over HTTPS with the pinned API version."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": USER_AGENT,
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if not url.startswith("https://api.github.com/"):
        message = f"refusing to fetch outside the GitHub API: {url}"
        raise PracticeInputError(message)
    request = urllib.request.Request(url, headers=headers)  # noqa: S310  # nosec B310
    try:
        # The scheme and host are fixed to the GitHub API above.
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
            body: bytes = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        message = f"cannot reach {url}: {error}"
        raise PracticeInputError(message) from error
    return body


def watch_findings(
    relative: str, upstreams: list[Upstream], timeout: float
) -> tuple[list[Finding], list[str]]:
    """Compare each watched upstream's latest release with what was last seen."""
    findings, notes = [], []
    for item in upstreams:
        if item.watch_type != "github-releases":
            notes.append(f"{item.name}: manual watch at {item.watch_target}; review is due by date")
            continue
        url = GITHUB_RELEASE_URL.format(repository=item.watch_target)
        version = release_version(fetch(url, timeout))
        if version != item.latest_seen.removeprefix("v"):
            message = (
                f"{item.name} released {version} (last seen {item.latest_seen}, pinned "
                f"{item.pinned}); incorporate it or record a hold"
            )
            findings.append(Finding(relative, 1, "upstream-released", message))
        else:
            notes.append(f"{item.name}: latest release {version} already seen")
    return findings, notes
