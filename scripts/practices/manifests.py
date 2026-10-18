"""Refuse doubling, fake-clock, fake-server, stand-in, and re-run packages in dependency manifests.

A mocking library that is installed gets used. Refusing it in the manifest
stops the shortcut before the first test reaches for it.
"""

from __future__ import annotations

import json
import re
import tomllib
from typing import TYPE_CHECKING

from .model import Finding
from .python_rules import DOUBLE_MESSAGES
from .script_rules import SCRIPT_PACKAGES

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path

PYTHON_PACKAGES: Mapping[str, str] = {
    "mock": "mock",
    "pytest-mock": "mock",
    "flexmock": "mock",
    "doublex": "mock",
    "freezegun": "fake-timer",
    "time-machine": "fake-timer",
    "pytest-freezer": "fake-timer",
    "responses": "fake-server",
    "respx": "fake-server",
    "requests-mock": "fake-server",
    "httpretty": "fake-server",
    "aioresponses": "fake-server",
    "pytest-httpserver": "fake-server",
    "pytest-localserver": "fake-server",
    "pytest-httpx": "fake-server",
    "fakeredis": "stand-in",
    "mongomock": "stand-in",
    "moto": "stand-in",
    "pyfakefs": "stand-in",
    "flaky": "rerun",
    "pytest-rerunfailures": "rerun",
}
CARGO_PACKAGES: Mapping[str, str] = {
    "mockall": "mock",
    "faux": "mock",
    "mockiato": "mock",
    "mockito": "fake-server",
    "wiremock": "fake-server",
    "httpmock": "fake-server",
}
NUGET_PACKAGES: Mapping[str, str] = {
    "moq": "mock",
    "nsubstitute": "mock",
    "fakeiteasy": "mock",
    "justmock": "mock",
    "wiremock.net": "fake-server",
    "microsoft.extensions.timeprovider.testing": "fake-timer",
}
GO_MODULES: Mapping[str, str] = {
    "github.com/golang/mock": "mock",
    "go.uber.org/mock": "mock",
    "github.com/jarcoal/httpmock": "fake-server",
    "github.com/jonboulle/clockwork": "fake-timer",
    "github.com/benbjohnson/clock": "fake-timer",
}
REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
# MSBuild reads attributes in any order and with either quote.
NUGET_ELEMENT = re.compile(
    r"<(?:Global)?Package(?:Reference|Version)\b(?P<attributes>[^>]*)>", re.IGNORECASE
)
NUGET_INCLUDE = re.compile(r"\bInclude\s*=\s*([\"'])(?P<name>.*?)\1", re.IGNORECASE)
NPM_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
CARGO_SECTIONS = ("dependencies", "dev-dependencies", "build-dependencies")


def python_name(requirement: str) -> str:
    """Normalize a PEP 508 requirement to its distribution name."""
    match = REQUIREMENT_NAME.match(requirement)
    return re.sub(r"[-_.]+", "-", match.group(1)).lower() if match else ""


def npm_names(text: str) -> Iterator[str]:
    """Yield every package named by package.json dependency sections."""
    data = json.loads(text)
    for section in NPM_SECTIONS:
        packages = data.get(section, {}) if isinstance(data, dict) else {}
        if isinstance(packages, dict):
            yield from packages


def requirement_lists(data: dict[str, object]) -> Iterator[object]:
    """Yield the requirement collections a pyproject.toml declares."""
    project = data.get("project", {})
    if isinstance(project, dict):
        yield project.get("dependencies", [])
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            yield from optional.values()
    groups = data.get("dependency-groups", {})
    if isinstance(groups, dict):
        yield from groups.values()
    tool = data.get("tool", {})
    poetry = tool.get("poetry", {}) if isinstance(tool, dict) else {}
    if isinstance(poetry, dict):
        yield list(poetry.get("dependencies", {}))
        yield list(poetry.get("dev-dependencies", {}))
        for group in poetry.get("group", {}).values():
            if isinstance(group, dict):
                yield list(group.get("dependencies", {}))


def pyproject_names(text: str) -> Iterator[str]:
    """Yield normalized distribution names from pyproject.toml."""
    for requirements in requirement_lists(tomllib.loads(text)):
        if isinstance(requirements, list):
            yield from (python_name(item) for item in requirements if isinstance(item, str))


def requirements_names(text: str) -> Iterator[str]:
    """Yield normalized names from a pip requirements file."""
    for line in text.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped and not stripped.startswith("-"):
            yield python_name(stripped)


def cargo_names(text: str) -> Iterator[str]:
    """Yield crate names from every dependency table in Cargo.toml."""
    data = tomllib.loads(text)
    tables = [data, *data.get("target", {}).values()]
    for table in tables:
        for section in CARGO_SECTIONS:
            dependencies = table.get(section, {}) if isinstance(table, dict) else {}
            if isinstance(dependencies, dict):
                yield from dependencies


def go_names(text: str) -> Iterator[str]:
    """Yield module paths required by go.mod."""
    for line in text.splitlines():
        words = line.split("//", 1)[0].split()
        if words and words[0] == "require":
            words = words[1:]
        if words and words[0] not in {"(", ")", "module", "go", "toolchain", "replace", "exclude"}:
            yield words[0]


def manifest_entries(path: Path, text: str) -> Iterator[tuple[str, str]]:
    """Yield (package, check) for each refused package in one manifest."""
    name = path.name.lower()
    if name == "package.json":
        yield from (
            (item, SCRIPT_PACKAGES[item]) for item in npm_names(text) if item in SCRIPT_PACKAGES
        )
    elif name == "pyproject.toml" or is_requirements_file(path):
        names = pyproject_names(text) if name == "pyproject.toml" else requirements_names(text)
        yield from ((item, PYTHON_PACKAGES[item]) for item in names if item in PYTHON_PACKAGES)
    elif name == "cargo.toml":
        yield from (
            (item, CARGO_PACKAGES[item]) for item in cargo_names(text) if item in CARGO_PACKAGES
        )
    elif path.suffix.lower() in {".csproj", ".fsproj", ".props"}:
        for element in NUGET_ELEMENT.finditer(text):
            include = NUGET_INCLUDE.search(element["attributes"])
            check = NUGET_PACKAGES.get(include["name"].lower()) if include else None
            if include and check:
                yield include["name"], check
    elif name == "go.mod":
        for module in go_names(text):
            check = next(
                (value for key, value in GO_MODULES.items() if module.startswith(key)), None
            )
            if check:
                yield module, check


def is_requirements_file(path: Path) -> bool:
    """Recognize requirements-*.txt files and any .txt or .in file in a requirements/ folder."""
    return path.suffix.lower() in {".txt", ".in"} and (
        path.name.lower().startswith("requirements") or path.parent.name.lower() == "requirements"
    )


def is_manifest(path: Path) -> bool:
    """Recognize the dependency manifests this check reads."""
    name = path.name.lower()
    return (
        name in {"package.json", "pyproject.toml", "cargo.toml", "go.mod"}
        or is_requirements_file(path)
        or path.suffix.lower() in {".csproj", ".fsproj"}
        or name in {"directory.packages.props", "directory.build.props"}
    )


def line_of(text: str, package: str) -> int:
    """Return the first line that names a package, or 1."""
    for number, line in enumerate(text.splitlines(), start=1):
        if package in line:
            return number
    return 1


def manifest_findings(path: Path, relative: str) -> list[Finding]:
    """Refuse doubling and re-run packages declared in one manifest."""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    try:
        entries = list(manifest_entries(path, text))
    except (ValueError, AttributeError, TypeError) as error:
        message = f"cannot parse this manifest, so its dependencies were not checked: {error}"
        return [Finding(relative, 1, "unparsed", message)]
    return [
        Finding(relative, line_of(text, package), check, f"{package} {DOUBLE_MESSAGES[check]}")
        for package, check in entries
    ]
