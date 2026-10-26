"""Guard against committing credentials in the Daedalus repository.

Run from repository root: python3 -m unittest discover -s .mcp/tests -t .mcp -v

Scan tracked and non-ignored untracked working-tree files, not Git history.
Personal data and infrastructure require a separate public-distribution review.
Findings report relative paths, line numbers and rules, never matched values.
These deliberately limited heuristics complement review; they cannot prove
that a repository contains no secrets. Generic assignments require at least
eight characters; in source code only direct string literals are checked.
"""

from __future__ import annotations

import re
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
PRIVATE_FILES = tuple(prefix + name for prefix in ("", "MCP/", ".mcp/") for name in
                      (".env", "tokens.json", "mcp.json", ".mcp_access_audit.jsonl", ".mcp_test_audit.jsonl"))


def _git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=False, capture_output=True,
        text=True, encoding="utf-8",
    )


from daedalus_validation.credentials import (
    PATTERNS, ALLOW_MARKER, MARKER_START, ASSIGNMENT, _is_placeholder, _scan_text,
)


def _candidate_files() -> list[Path]:
    result = _git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    if result.returncode != 0:
        raise RuntimeError("git ls-files falhou; a auditoria não foi executada.")
    # Deleted paths are absent; unreadable existing paths must still be checked.
    return sorted({ROOT / item for item in result.stdout.split("\0")
                   if item and ((ROOT / item).exists() or (ROOT / item).is_symlink())})


def _sensitive_filename(path: Path) -> bool:
    name = path.name.lower()
    if name.startswith(".env") and name not in {".env.example", ".env.template", ".env.sample"}:
        return True
    return (
        name in {"tokens.json", "id_rsa", "id_ed25519", "credentials.json", "service-account.json"}
        or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
    )


def _scan_file(path: Path) -> list[tuple[int, str]]:
    try:
        data = path.read_bytes()
    except OSError:
        return [(1, "READ_ERROR")]
    if b"\0" in data:
        return []  # Binary content is outside this text audit.
    return _scan_text(
        data.decode("utf-8", errors="replace"),
        source_code=path.suffix.lower() in {".py", ".js", ".ts", ".jsx", ".tsx"},
    )


class CredentialDetectorTests(unittest.TestCase):
    @staticmethod
    def _marker(value="synthetic.value", rule="CREDENTIAL_ASSIGNMENT", reason="Exemplo didático"):
        return ("# daedalus-scan: allow " + rule + " value=" + json.dumps(value)
                + " reason=" + json.dumps(reason))

    def test_marker_allows_exact_value_on_next_line(self):
        marker = self._marker()
        assignment = "password=" + "synthetic.value"
        self.assertEqual(_scan_text(marker + "\n" + assignment), [])
        html = "<!-- " + marker[2:] + " -->"
        self.assertEqual(_scan_text(html + "\n" + assignment), [])

    def test_marker_does_not_allow_other_values_or_rules(self):
        sample = self._marker() + "\npassword=" + "different.value"
        self.assertEqual(_scan_text(sample), [(2, "CREDENTIAL_ASSIGNMENT")])
        sample = self._marker(rule="PROVIDER_TOKEN") + "\npassword=" + "synthetic.value"
        self.assertEqual(_scan_text(sample), [(2, "CREDENTIAL_ASSIGNMENT")])

    def test_marker_expires_after_next_line(self):
        assignment = "password=" + "synthetic.value"
        for separator in ("\n", "text\n"):
            self.assertEqual(_scan_text(self._marker() + "\n" + separator + assignment),
                             [(3, "CREDENTIAL_ASSIGNMENT")])
        self.assertEqual(_scan_text(self._marker() + "\n" + assignment + "\n" + assignment),
                         [(3, "CREDENTIAL_ASSIGNMENT")])

    def test_marker_only_exempts_one_match(self):
        assignment = "password=" + "synthetic.value"
        sample = self._marker() + "\n" + assignment + " " + assignment
        self.assertEqual(_scan_text(sample), [(2, "CREDENTIAL_ASSIGNMENT")])
        sample = self._marker() + "\n" + assignment + " token=" + "another.value"
        self.assertEqual(_scan_text(sample), [(2, "CREDENTIAL_ASSIGNMENT")])

    def test_marker_provider_exception_is_exact(self):
        value = "gh" + "p_" + "A" * 24
        marker = self._marker(value=value, rule="PROVIDER_TOKEN")
        self.assertEqual(_scan_text(marker + "\n" + value), [])
        self.assertEqual(_scan_text(marker + "\n" + value + "B"), [(2, "PROVIDER_TOKEN")])

    def test_invalid_markers_fail_explicitly(self):
        for marker in (self._marker(rule="UNKNOWN"), self._marker(reason=" "),
                       self._marker(value=""), self._marker() + " extra",
                       "<!-- " + self._marker()[2:], self._marker() + " -->"):
            with self.subTest(marker=marker):
                sample = marker + "\npassword=" + "synthetic.value"
                self.assertIn((1, "INVALID_ALLOW_MARKER"), _scan_text(sample))
                self.assertIn((2, "CREDENTIAL_ASSIGNMENT"), _scan_text(sample))

    def test_recognizes_credential_categories(self):
        samples = {
            "PROVIDER_TOKEN": "gh" + "p_" + "A" * 24,
            "AWS_ACCESS_KEY_ID": "AK" + "IA" + "A" * 16,
            "DAEDALUS_TOKEN": "daedalus_" + "sec_" + "a" * 64,
            "PRIVATE_KEY": "-----BEGIN " + "PRIVATE" + " KEY-----",
            "CREDENTIAL_ASSIGNMENT": 'password="' + "synthetic" + ".value(123)" + '"',
        }
        for rule, sample in samples.items():
            with self.subTest(rule=rule):
                self.assertIn((1, rule), _scan_text(sample))

    def test_context_is_allowed(self):
        self.assertEqual(_scan_text(
            "email=contato@example.org\npath=/caminho/usuario/daedalus\n"
            "host=servidor-exemplo\nip=192.0.2.10\nipv6=2001:db8::1"
        ), [])

    def test_placeholders_and_variable_references_are_allowed(self):
        self.assertEqual(_scan_text(
            'API_KEY=your_placeholder_value\nPASSWORD=${DB_PASSWORD}\n'
            'key: ${{ secrets.SSH_PRIVATE_KEY }}\npassword="<SUA_SENHA>"\n'
            'token="daedalus_sec_REPLACE_WITH_REAL_TOKEN_HERE"'
        ), [])

    def test_checks_later_assignments_after_placeholder(self):
        sample = 'password=your_placeholder token="' + "synthetic" + '.value"'
        self.assertEqual(_scan_text(sample), [(1, "CREDENTIAL_ASSIGNMENT")])

    def test_example_word_inside_literal_is_not_an_exemption(self):
        sample = 'password="' + "synthetic" + '-example.value"'
        self.assertEqual(_scan_text(sample), [(1, "CREDENTIAL_ASSIGNMENT")])

    def test_source_expressions_are_allowed(self):
        self.assertEqual(_scan_text('token = obj.get("token")'), [])
        self.assertEqual(_scan_text('const token = tokenizer.current;', source_code=True), [])
        self.assertEqual(_scan_text('password="base_" + suffix', source_code=True), [])

    def test_quoted_credentials_in_source_are_detected(self):
        sample = "".join(("token", "=", chr(34), "synthetic.value", chr(34)))
        self.assertEqual(_scan_text(sample, source_code=True), [(1, "CREDENTIAL_ASSIGNMENT")])

    def test_equality_is_not_a_credential_assignment(self):
        self.assertEqual(_scan_text('password===someExpression', source_code=True), [])

    def test_aws_like_substrings_in_encoded_assets_are_not_keys(self):
        self.assertEqual(_scan_text('prefix' + 'AK' + 'IA' + 'A' * 16 + 'suffix'), [])

    def test_sensitive_filenames_and_templates(self):
        for name in (".env", ".env.local", "tokens.json", "private.pem"):
            with self.subTest(name=name):
                self.assertTrue(_sensitive_filename(Path(name)))
        for name in (".env.example", "tokens.example.json", "document.md"):
            with self.subTest(name=name):
                self.assertFalse(_sensitive_filename(Path(name)))

    def test_read_errors_are_reported(self):
        with patch.object(Path, "read_bytes", side_effect=PermissionError):
            self.assertEqual(_scan_file(Path("unreadable.md")), [(1, "READ_ERROR")])


class RepositoryCredentialTests(unittest.TestCase):
    def test_relocated_scanner_covers_knowledge_outside_application_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            (root / "wiki").mkdir()
            (root / ".mcp").mkdir()
            note = root / "wiki/Synthetic.md"
            note.write_text("password=" + "synthetic.value\n")
            (root / ".gitignore").write_text("tokens.json\n")
            private = root / ".mcp/tokens.json"
            private.write_text("Private fixture\n")
            with patch(__name__ + ".ROOT", root):
                candidates = _candidate_files()
                self.assertIn(note, candidates)
                self.assertNotIn(private, candidates)
                self.assertEqual(_scan_file(note), [(1, "CREDENTIAL_ASSIGNMENT")])

    def test_private_files_are_ignored_and_untracked(self):
        tracked = _git("ls-files", "-z")
        self.assertEqual(tracked.returncode, 0, "Não foi possível consultar o índice Git.")
        tracked_paths = set(tracked.stdout.split("\0"))
        for name in PRIVATE_FILES:
            with self.subTest(path=name):
                self.assertNotIn(name, tracked_paths)
                self.assertEqual(_git("check-ignore", "--quiet", "--", name).returncode, 0)

    def test_working_tree_has_no_credentials(self):
        findings = []
        for path in _candidate_files():
            if _sensitive_filename(path):
                findings.append(f"{path.relative_to(ROOT)}:1: SENSITIVE_FILENAME")
            for number, rule in _scan_file(path):
                findings.append(f"{path.relative_to(ROOT)}:{number}: {rule}")
        self.assertFalse(findings, "Possíveis credenciais (valores omitidos):\n" + "\n".join(findings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
