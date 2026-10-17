"""Prove verify-practices refuses each harmful practice and accepts the legitimate form beside it.

Every case writes a real project to a temporary directory and runs the real
command. Each refused form is paired with a negative control that must pass, so a
check that fired on everything would fail here as surely as one that fired on
nothing.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import override

from scripts.practices.cli import run
from scripts.practices.model import PracticeInputError
from scripts.practices.upstreams import GITHUB_RELEASE_URL, fetch, release_version

ROOT = Path(__file__).resolve().parents[1]
# (label, files to add or remove, path inspected, expected check or None for clean)
type Case = tuple[str, Mapping[str, str | None], str, str | None]
SCRIPT = ROOT / "scripts" / "verify-practices.py"
# A public repository with regular tagged releases, queried live by the watch test.
LIVE_REPOSITORY = "gitleaks/gitleaks"
TODAY = datetime.now(tz=UTC).date()
REGISTER = '# Rules\n\n```pitfalls-register\n{"schema_version": 1, "pitfalls": []}\n```\n'
WORKFLOW = """name: Quality
"on":
  pull_request:
  merge_group:
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - run: python -m unittest
"""


def upstream(**changes: object) -> dict[str, object]:
    """Return one valid upstream entry with selected fields replaced."""
    entry: dict[str, object] = {
        "name": "example-cli",
        "kind": "cli",
        "pinned": "1.2.3",
        "used_in": ["tools.txt"],
        "watch": {"type": "manual", "url": "https://example.com/releases"},
        "reviewed": TODAY.isoformat(),
        "latest_seen": "1.2.3",
        "max_age_days": 30,
        "hold": None,
    }
    entry.update(changes)
    return entry


def upstreams_json(*entries: dict[str, object]) -> str:
    """Serialize an upstreams.json document."""
    return json.dumps({"schema_version": 1, "upstreams": list(entries or (upstream(),))})


BASE_FILES = {
    "AGENTS.md": REGISTER,
    "upstreams.json": upstreams_json(),
    "tools.txt": "example-cli 1.2.3\n",
    "src/app.py": "def add(left: int, right: int) -> int:\n    return left + right\n",
    "tests/test_app.py": (
        "from src.app import add\n\n\ndef test_add() -> None:\n    assert add(2, 3) == 5\n"
    ),
}


class PracticeProject:
    """A disposable project written to disk and checked by the real command."""

    def __init__(self, case: unittest.TestCase, files: Mapping[str, str | None]) -> None:
        """Write the base project, then apply additions (text) and removals (None)."""
        temporary = tempfile.TemporaryDirectory(prefix="practices-")
        case.addCleanup(temporary.cleanup)
        self.case = case
        self.root = Path(temporary.name)
        for relative, text in {**BASE_FILES, **files}.items():
            path = self.root / relative
            if text is None:
                path.unlink(missing_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def check(self) -> tuple[int, dict[str, object]]:
        """Run the command in-process and return its exit code and JSON report."""
        code, output = run(["--root", str(self.root), "--format", "json"])
        report = json.loads(output) if output.startswith("{") else {"error": output}
        return code, report

    def found(self) -> set[tuple[str, str]]:
        """Return (path, check) for every finding."""
        _, report = self.check()
        findings = report.get("findings")
        if not isinstance(findings, list):
            self.case.fail(f"the command returned no findings list: {report}")
        return {(item["path"], item["check"]) for item in findings}


class PracticeCommandTests(unittest.TestCase):
    """Refused forms fail, legitimate forms pass, and the command keeps its exit contract."""

    @override
    def setUp(self) -> None:
        """Keep failure output complete for diagnosis."""
        self.maxDiff = None

    def assert_cases(self, cases: list[Case]) -> None:
        """Check (label, files, path, check) cases; None means the path must stay clean."""
        for label, files, path, check in cases:
            with self.subTest(label):
                found = PracticeProject(self, files).found()
                if check is None:
                    self.assertEqual({item for item in found if item[0] == path}, set())
                else:
                    self.assertIn((path, check), found)

    def command(self, script: Path, root: Path) -> subprocess.CompletedProcess[str]:
        """Start the gate as a child process, exactly as CI starts it."""
        # Trusted interpreter and checked-in or linked entry script; no shell.
        return subprocess.run(  # noqa: S603  # nosec B603
            [sys.executable, str(script), "--root", str(root)],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    def test_command_exit_contract(self) -> None:
        """Clean passes; a planted violation, missing input, or no code never passes."""
        cases: tuple[tuple[str, Mapping[str, str | None], int, str], ...] = (
            ("clean project", {}, 0, "PASS"),
            ("planted mock", {"tests/test_app.py": "from unittest import mock\n"}, 1, "mock"),
            ("no upstreams.json", {"upstreams.json": None}, 1, "upstreams-missing"),
            ("unparseable upstreams.json", {"upstreams.json": "{"}, 2, "cannot be read as JSON"),
            ("no code", {"src/app.py": None, "tests/test_app.py": None}, 1, "nothing-scanned"),
        )
        for label, files, code, text in cases:
            with self.subTest(label):
                project = PracticeProject(self, files)
                result = self.command(SCRIPT, project.root)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertIn(text, result.stdout)
        missing = self.command(SCRIPT, Path(tempfile.gettempdir()) / "practices-missing-root")
        self.assertEqual(missing.returncode, 2, missing.stdout)
        self.assertIn("not a directory", missing.stdout)

    def test_command_started_through_symlink(self) -> None:
        """An installed link to the entry script still finds its package and fails on violations."""
        links = Path(tempfile.mkdtemp(prefix="practices-link-"))
        self.addCleanup(shutil.rmtree, links)
        link = links / "verify-practices.py"
        try:
            link.symlink_to(SCRIPT)
        except OSError as error:
            self.skipTest(f"this host cannot create symlinks: {error}")
        clean = PracticeProject(self, {})
        self.assertEqual(self.command(link, clean.root).returncode, 0)
        planted = PracticeProject(self, {"tests/test_app.py": "import freezegun\n"})
        result = self.command(link, planted.root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("fake-timer", result.stdout)

    def test_test_doubles_are_refused_in_every_language(self) -> None:
        """Mocks, fake clocks, fake servers, stand-ins, and re-runs fail; mentions do not."""
        go_server = (
            'package app\nimport ("net/http"; "net/http/httptest")\n'
            "func TestX() { httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, "
            "r *http.Request) {})) }\n"
        )
        mentions = (
            '"""Mentions of unittest.mock in text never count."""\n'
            "# from unittest import mock\n"
            "NOTE = \"vi.mock('x')\"\n\n\n"
            "def test_env(monkeypatch) -> None:\n"
            '    monkeypatch.setenv("MODE", "real")\n'
        )
        script_mentions = (
            '// vi.mock("x") is refused\nconst note = "jest.fn()";\n'
            "const pattern = /vi\\.mock\\(/;\n"
            'test("adds", () => { expect(add(1, 2)).toBe(3); });\n'
        )
        cases: list[Case] = [
            (
                "python mock import",
                {"tests/t1.py": "from unittest import mock\n"},
                "tests/t1.py",
                "mock",
            ),
            (
                "python monkeypatch.setattr",
                {"tests/t2.py": "def test_x(monkeypatch):\n    monkeypatch.setattr(a, 'b', 1)\n"},
                "tests/t2.py",
                "mock",
            ),
            (
                "python mocker fixture",
                {"tests/t3.py": "def test_x(mocker):\n    pass\n"},
                "tests/t3.py",
                "mock",
            ),
            (
                "python fake clock",
                {"tests/t4.py": "from freezegun import freeze_time\n"},
                "tests/t4.py",
                "fake-timer",
            ),
            (
                "python hand-written server",
                {
                    "tests/t5.py": (
                        "import http.server\n"
                        "class H(http.server.BaseHTTPRequestHandler):\n    pass\n"
                    )
                },
                "tests/t5.py",
                "fake-server",
            ),
            (
                "python store stand-in",
                {"tests/t6.py": "import fakeredis\n"},
                "tests/t6.py",
                "stand-in",
            ),
            (
                "python re-run marker",
                {
                    "tests/t7.py": (
                        "import pytest\n@pytest.mark.flaky(reruns=2)\ndef test_x():\n    pass\n"
                    )
                },
                "tests/t7.py",
                "rerun",
            ),
            ("python mentions and setenv", {"tests/t8.py": mentions}, "tests/t8.py", None),
            (
                "script module mock",
                {"tests/a.test.ts": 'vi.mock("../src/app");\n'},
                "tests/a.test.ts",
                "mock",
            ),
            (
                "script spy",
                {"tests/b.test.ts": "jest.spyOn(api, 'get');\n"},
                "tests/b.test.ts",
                "mock",
            ),
            (
                "script fake clock",
                {"tests/c.test.ts": "vi.useFakeTimers();\n"},
                "tests/c.test.ts",
                "fake-timer",
            ),
            (
                "script fake server",
                {"tests/d.test.ts": 'import nock from "nock";\n'},
                "tests/d.test.ts",
                "fake-server",
            ),
            (
                "script stand-in",
                {"tests/e.test.ts": 'import { vol } from "memfs";\n'},
                "tests/e.test.ts",
                "stand-in",
            ),
            (
                "script retries",
                {"tests/f.test.js": "jest.retryTimes(3);\n"},
                "tests/f.test.js",
                "rerun",
            ),
            ("script mentions", {"tests/g.test.ts": script_mentions}, "tests/g.test.ts", None),
            ("csharp", {"tests/AppTests.cs": "using Moq;\n"}, "tests/AppTests.cs", "mock"),
            ("rust", {"tests/app.rs": "use mockall::predicate::*;\n"}, "tests/app.rs", "mock"),
            (
                "go mock",
                {"app_test.go": 'import "github.com/golang/mock/gomock"\n'},
                "app_test.go",
                "mock",
            ),
            ("go handler server", {"server_test.go": go_server}, "server_test.go", "fake-server"),
            (
                "java",
                {"src/test/java/AppTest.java": "import org.mockito.Mockito;\n"},
                "src/test/java/AppTest.java",
                "mock",
            ),
            (
                "pester",
                {"tests/App.Tests.ps1": "Mock Get-Date { 1 }\n"},
                "tests/App.Tests.ps1",
                "mock",
            ),
            (
                "jest manual mocks",
                {"src/__mocks__/fs.js": "module.exports = {};\n"},
                "src/__mocks__",
                "mock",
            ),
            (
                "npm manifest",
                {"package.json": '{"devDependencies": {"sinon": "^17"}}'},
                "package.json",
                "mock",
            ),
            (
                "pyproject manifest",
                {
                    "pyproject.toml": (
                        '[project]\nname = "x"\n'
                        'optional-dependencies = {test = ["pytest-mock>=3"]}\n'
                    )
                },
                "pyproject.toml",
                "mock",
            ),
            (
                "requirements manifest",
                {"requirements-dev.txt": "freezegun==1.5\n"},
                "requirements-dev.txt",
                "fake-timer",
            ),
            (
                "cargo manifest",
                {"Cargo.toml": '[dev-dependencies]\nmockall = "0.13"\n'},
                "Cargo.toml",
                "mock",
            ),
            (
                "nuget manifest",
                {
                    "tests/App.Tests.csproj": (
                        '<Project><ItemGroup><PackageReference Include="Moq" />'
                        "</ItemGroup></Project>"
                    )
                },
                "tests/App.Tests.csproj",
                "mock",
            ),
            (
                "go manifest",
                {"go.mod": "module x\nrequire go.uber.org/mock v0.4.0\n"},
                "go.mod",
                "mock",
            ),
        ]
        self.assert_cases(cases)

    def test_tests_must_be_able_to_fail_a_user(self) -> None:
        """Presence-only, finding-named, and copied tests are refused; behavior tests pass."""
        presence = (
            "from pathlib import Path\n\n\ndef test_readme_mentions_install() -> None:\n"
            '    text = Path("README.md").read_text(encoding="utf-8")\n'
            '    assert "npm install" in text\n'
        )
        behavior = (
            "import subprocess\nimport sys\n\n\ndef test_usage() -> None:\n"
            "    result = subprocess.run([sys.executable, '-c', 'print(1)'], capture_output=True, "
            "text=True, check=False)\n"
            '    assert "1" in result.stdout\n'
        )
        parses = (
            "import json\nfrom pathlib import Path\n\n\ndef test_config_loads() -> None:\n"
            '    assert isinstance(json.loads(Path("c.json").read_text()), dict)\n'
        )
        copies = "".join(
            f"def test_case_{index}() -> None:\n    assert add({index}, 1) == {index + 1}\n\n\n"
            for index in range(3)
        )
        two_copies = "".join(
            f"def test_case_{index}() -> None:\n    assert add({index}, 1) == {index + 1}\n\n\n"
            for index in range(2)
        )
        script_presence = (
            'import { readFileSync } from "node:fs";\n'
            'test("readme", () => {\n'
            '  expect(readFileSync("README.md", "utf8")).toContain("npm");\n'
            "});\n"
        )
        script_copies = "".join(
            f'test("adds {index}", () => {{ expect(add({index}, 1)).toBe({index + 1}); }});\n'
            for index in range(3)
        )
        cases: list[Case] = [
            (
                "python presence only",
                {"tests/test_docs.py": presence},
                "tests/test_docs.py",
                "text-existence",
            ),
            (
                "python behavior with output text",
                {"tests/test_cli.py": behavior},
                "tests/test_cli.py",
                None,
            ),
            ("python grammar check", {"tests/test_cfg.py": parses}, "tests/test_cfg.py", None),
            ("python three copies", {"tests/test_add.py": copies}, "tests/test_add.py", "one-off"),
            ("python two copies", {"tests/test_add.py": two_copies}, "tests/test_add.py", None),
            (
                "python finding-named test",
                {
                    "tests/test_x.py": (
                        "def test_finding_12_empty() -> None:\n    assert add(0, 0) == 0\n"
                    )
                },
                "tests/test_x.py",
                "one-off",
            ),
            (
                "script presence only",
                {"tests/docs.test.ts": script_presence},
                "tests/docs.test.ts",
                "text-existence",
            ),
            (
                "script behavior",
                {"tests/add.test.ts": 'test("adds", () => { expect(add(1, 2)).toBe(3); });\n'},
                "tests/add.test.ts",
                None,
            ),
            (
                "script three copies",
                {"tests/add.test.ts": script_copies},
                "tests/add.test.ts",
                "one-off",
            ),
            (
                "script finding-titled test",
                {
                    "tests/x.test.ts": (
                        'test("finding 7: rejects empty", () => {\n  expect(f("")).toBe(0);\n});\n'
                    )
                },
                "tests/x.test.ts",
                "one-off",
            ),
        ]
        self.assert_cases(cases)

    def test_waits_timeouts_and_retries(self) -> None:
        """Fixed delays, per-test timeout overrides, and configured retries are refused."""
        cases: list[Case] = [
            (
                "python sleep",
                {"tests/t.py": "import time\ntime.sleep(2)\n"},
                "tests/t.py",
                "fixed-delay",
            ),
            (
                "python yield",
                {"tests/t.py": "import asyncio\nasyncio.sleep(0)\n"},
                "tests/t.py",
                None,
            ),
            (
                "python timeout marker",
                {
                    "tests/t.py": (
                        "import pytest\n@pytest.mark.timeout(60)\ndef test_x():\n    pass\n"
                    )
                },
                "tests/t.py",
                "timeout-override",
            ),
            ("product sleep", {"src/poll.py": "import time\ntime.sleep(2)\n"}, "src/poll.py", None),
            (
                "playwright wait",
                {"tests/a.spec.ts": "await page.waitForTimeout(500);\n"},
                "tests/a.spec.ts",
                "fixed-delay",
            ),
            (
                "promise sleep",
                {"tests/b.test.ts": "await new Promise((r) => setTimeout(r, 100));\n"},
                "tests/b.test.ts",
                "fixed-delay",
            ),
            (
                "per-test timeout",
                {"tests/c.test.ts": 'test("slow", async () => { await run(); }, 30000);\n'},
                "tests/c.test.ts",
                "timeout-override",
            ),
            (
                "retry option",
                {"tests/d.test.ts": 'test("x", { retry: 2 }, () => { run(); });\n'},
                "tests/d.test.ts",
                "rerun",
            ),
            (
                "go sleep",
                {"app_test.go": "time.Sleep(time.Second)\n"},
                "app_test.go",
                "fixed-delay",
            ),
            (
                "playwright retries",
                {"playwright.config.ts": "export default { retries: process.env.CI ? 2 : 0 };\n"},
                "playwright.config.ts",
                "rerun",
            ),
            (
                "no retries",
                {"playwright.config.ts": "export default { retries: 0 };\n"},
                "playwright.config.ts",
                None,
            ),
            (
                "pytest reruns",
                {"pyproject.toml": '[tool.pytest.ini_options]\naddopts = "--reruns 3"\n'},
                "pyproject.toml",
                "rerun",
            ),
        ]
        self.assert_cases(cases)

    def test_allowances_are_reviewed_exceptions(self) -> None:
        """An allowance needs a reason, a matching finding, and a check that permits one."""
        sleep = "import time\ntime.sleep(2)"
        reviewed = "  # verify-practices: allow fixed-delay -- documented server backoff\n"
        no_reason = "  # verify-practices: allow fixed-delay\n"
        cases: list[Case] = [
            ("reviewed allowance", {"tests/t.py": sleep + reviewed}, "tests/t.py", None),
            (
                "allowance without reason keeps the finding",
                {"tests/t.py": sleep + no_reason},
                "tests/t.py",
                "fixed-delay",
            ),
            (
                "allowance without reason is reported",
                {"tests/t.py": sleep + no_reason},
                "tests/t.py",
                "allowance-invalid",
            ),
            (
                "stale allowance",
                {"tests/t.py": "# verify-practices: allow fixed-delay -- old\nimport time\n"},
                "tests/t.py",
                "allowance-unused",
            ),
            (
                "allowance on a mock",
                {"tests/t.py": "from unittest import mock  # verify-practices: allow mock -- x\n"},
                "tests/t.py",
                "allowance-refused",
            ),
            (
                "unknown check",
                {"tests/t.py": "import time  # verify-practices: allow vibes -- because\n"},
                "tests/t.py",
                "allowance-invalid",
            ),
        ]
        self.assert_cases(cases)

    def test_merge_gate_workflows(self) -> None:
        """Gate workflows report on every change, need no secret, never re-run, and time out."""
        gate = ".github/workflows/ci.yml"
        release = (
            'name: Release\n"on":\n  push:\n    tags: ["v*"]\njobs:\n  publish:\n'
            "    runs-on: ubuntu-latest\n    timeout-minutes: 10\n    steps:\n"
            "      - run: publish\n        env:\n          TOKEN: ${{ secrets.NPM_TOKEN }}\n"
        )
        reusable = (
            'name: R\n"on":\n  pull_request:\n  merge_group:\njobs:\n  gates:\n'
            "    uses: ./.github/workflows/other.yml\n"
        )
        cases: list[Case] = [
            ("clean gate", {gate: WORKFLOW}, gate, None),
            (
                "no merge_group",
                {gate: WORKFLOW.replace("  merge_group:\n", "")},
                gate,
                "ci-merge-group",
            ),
            (
                "path filter",
                {
                    gate: WORKFLOW.replace(
                        "  pull_request:\n", "  pull_request:\n    paths: [src/**]\n"
                    )
                },
                gate,
                "ci-path-filter",
            ),
            (
                "secret in gate",
                {gate: WORKFLOW + "        env:\n          KEY: ${{ secrets.API_KEY }}\n"},
                gate,
                "ci-secret",
            ),
            (
                "continue-on-error",
                {
                    gate: WORKFLOW.replace(
                        "    timeout-minutes: 15\n",
                        "    timeout-minutes: 15\n    continue-on-error: true\n",
                    )
                },
                gate,
                "ci-continue-on-error",
            ),
            (
                "no timeout",
                {gate: WORKFLOW.replace("    timeout-minutes: 15\n", "")},
                gate,
                "ci-timeout",
            ),
            (
                "retry action",
                {
                    gate: WORKFLOW
                    + "      - uses: nick-fields/retry@ce71cc2ab81d554ebbe88c79ab5975992d79ba08\n"
                },
                gate,
                "rerun",
            ),
            ("fixed sleep", {gate: WORKFLOW + "      - run: sleep 30\n"}, gate, "fixed-delay"),
            (
                "release secret",
                {".github/workflows/release.yml": release},
                ".github/workflows/release.yml",
                None,
            ),
            ("reusable call", {gate: reusable}, gate, None),
        ]
        for template in ("quality.yml", "upstream-watch.yml"):
            shipped = (ROOT / "templates" / "ci" / template).read_text(encoding="utf-8")
            target = f".github/workflows/{template}"
            cases.append((f"shipped {template}", {target: shipped}, target, None))
        self.assert_cases(cases)

    def test_upstream_currency(self) -> None:
        """Lapsed reviews, unheld lag, expired holds, and pin drift fail; current pins pass."""
        hold = {
            "reason": "waiting for a compatible plugin",
            "until": (TODAY + timedelta(days=9)).isoformat(),
        }
        expired = {"reason": "old decision", "until": (TODAY - timedelta(days=1)).isoformat()}
        old = (TODAY - timedelta(days=40)).isoformat()
        cases: list[Case] = [
            ("current", {}, "upstreams.json", None),
            (
                "review overdue",
                {"upstreams.json": upstreams_json(upstream(reviewed=old))},
                "upstreams.json",
                "upstream-review-overdue",
            ),
            (
                "behind",
                {"upstreams.json": upstreams_json(upstream(latest_seen="1.3.0"))},
                "upstreams.json",
                "upstream-behind",
            ),
            (
                "held",
                {"upstreams.json": upstreams_json(upstream(latest_seen="1.3.0", hold=hold))},
                "upstreams.json",
                None,
            ),
            (
                "hold expired",
                {"upstreams.json": upstreams_json(upstream(latest_seen="1.3.0", hold=expired))},
                "upstreams.json",
                "upstream-hold-expired",
            ),
            (
                "pin drift",
                {"tools.txt": "example-cli 1.2.4\n"},
                "upstreams.json",
                "upstream-pin-drift",
            ),
        ]
        self.assert_cases(cases)
        malformed = (
            ("unknown field", upstreams_json(upstream(extra=1))),
            ("bad date", upstreams_json(upstream(reviewed="last week"))),
            (
                "future review",
                upstreams_json(upstream(reviewed=(TODAY + timedelta(days=2)).isoformat())),
            ),
            ("bad watch", upstreams_json(upstream(watch={"type": "rss", "url": "https://x"}))),
            ("duplicate key", '{"schema_version": 1, "schema_version": 1, "upstreams": []}'),
        )
        for label, text in malformed:
            with self.subTest(label):
                code, report = PracticeProject(self, {"upstreams.json": text}).check()
                self.assertEqual(code, 2, report)
                self.assertIn("upstreams.json", str(report["error"]))

    def test_release_watch_queries_github_live(self) -> None:
        """The watch reads a real latest release from GitHub; malformed bodies are input errors.

        This calls api.github.com for real. An unreachable API fails the test: the
        outside world is tested live or not at all, never through a recording.
        """
        url = GITHUB_RELEASE_URL.format(repository=LIVE_REPOSITORY)
        version = release_version(fetch(url, timeout=30))
        self.assertRegex(version, r"^\d+(\.\d+)+")
        for body in (b"<html>rate limited</html>", b'{"message": "Not Found"}'):
            with self.subTest(body), self.assertRaises(PracticeInputError):
                release_version(body)

    def test_pitfalls_register_is_enforced_by_code(self) -> None:
        """Each pitfall names a test, a CI-run gate, or a built-in check; prose never counts."""

        def register(*enforcement: dict[str, str]) -> str:
            entry = {"id": "PIT-1", "pitfall": "p", "rule": "r", "enforced_by": list(enforcement)}
            return REGISTER.replace('"pitfalls": []', f'"pitfalls": [{json.dumps(entry)}]')

        gate = {
            "scripts/check_x.py": "print('x')\n",
            ".github/workflows/ci.yml": WORKFLOW + "      - run: python scripts/check_x.py\n",
        }
        cases: list[Case] = [
            (
                "test and check",
                {"AGENTS.md": register({"path": "tests/test_app.py"}, {"check": "mock"})},
                "AGENTS.md",
                None,
            ),
            (
                "gate run by CI",
                {**gate, "AGENTS.md": register({"path": "scripts/check_x.py"})},
                "AGENTS.md",
                None,
            ),
            (
                "document named by CI",
                {
                    "docs/RULES.md": "Never mock.\n",
                    ".github/workflows/ci.yml": WORKFLOW + "      - run: cat docs/RULES.md\n",
                    "AGENTS.md": register({"path": "docs/RULES.md"}),
                },
                "AGENTS.md",
                "register-unenforced",
            ),
            (
                "script CI never runs",
                {
                    "scripts/check_x.py": "print('x')\n",
                    "AGENTS.md": register({"path": "scripts/check_x.py"}),
                },
                "AGENTS.md",
                "register-unenforced",
            ),
            (
                "unknown check",
                {"AGENTS.md": register({"check": "vibes"})},
                "AGENTS.md",
                "register-unenforced",
            ),
            ("no enforcement", {"AGENTS.md": register()}, "AGENTS.md", "register-unenforced"),
            ("no register", {"AGENTS.md": "# Rules\n"}, "AGENTS.md", "register-missing"),
        ]
        self.assert_cases(cases)
        for label, text in (
            ("malformed", REGISTER.replace("[]", "[")),
            ("two blocks", REGISTER + REGISTER),
        ):
            with self.subTest(label):
                code, report = PracticeProject(self, {"AGENTS.md": text}).check()
                self.assertEqual(code, 2, report)
                self.assertIn("pitfalls register", str(report["error"]))

    def test_shipped_project_templates(self) -> None:
        """The rules template carries a valid empty register; the pin template demands real data."""
        templates = ROOT / "templates" / "workflow"
        rules = (templates / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(PracticeProject(self, {"AGENTS.md": rules}).found(), set())
        pins = (templates / "upstreams.json").read_text(encoding="utf-8")
        code, report = PracticeProject(self, {"upstreams.json": pins}).check()
        self.assertEqual(code, 2, report)


if __name__ == "__main__":
    unittest.main()
