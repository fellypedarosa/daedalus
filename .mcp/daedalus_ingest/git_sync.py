"""Host-only publisher. Uses Git plumbing, a private index and isolated merges."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .publication import coordination, publication_status, sync_root
from .sources import path_for
from .storage import IngestError, sha, write_json

HEX = re.compile(r"[0-9a-f]{64}\Z")
OP_ID = re.compile(r"[0-9a-f]{32}\Z")


class GitFailure(IngestError):
    def __init__(self, command):
        # Git diagnostics can contain credential-bearing URLs; keep them out
        # of private receipts and MCP replies as well as normal console logs.
        super().__init__("pending", "Git operation failed; publication remains saved", command=command)


class Publisher:
    def __init__(self, root, *, attempts=3):
        self.root = Path(root).resolve()
        self.base = sync_root(self.root)
        self.attempts = attempts

    def git(self, *args, data=None, env=None, check=True, cwd=None):
        environment = dict(os.environ)
        # Never inherit another command's private index, worktree or object DB.
        contexts = {"GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS"}
        for key in list(environment):
            if key in contexts or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
                environment.pop(key)
        environment.update({"GIT_TERMINAL_PROMPT": "0", "GIT_LITERAL_PATHSPECS": "1"})
        environment.update(env or {})
        try:
            result = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
                                     "-c", "user.name=Daedalus Ingest", "-c", "user.email=daedalus@localhost",
                                     *args], cwd=cwd or self.root, env=environment, input=data,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        except (OSError, subprocess.TimeoutExpired):
            raise GitFailure(args[0]) from None
        if check and result.returncode:
            raise GitFailure(args[0])
        return result

    def oid(self, reference):
        r = self.git("rev-parse", "--verify", reference, check=False)
        return r.stdout.decode().strip() if r.returncode == 0 else None

    def ancestor(self, older, newer):
        return self.git("merge-base", "--is-ancestor", older, newer, check=False).returncode == 0

    def tree_value(self, revision, path):
        r = self.git("ls-tree", "-z", revision, "--", path)
        if not r.stdout:
            return None
        header, name = r.stdout.rstrip(b"\0").split(b"\t", 1)
        mode, kind, oid = header.split()
        if mode != b"100644" or kind != b"blob" or name.decode() != path:
            raise IngestError("conflict", "Expected a regular Markdown file in Git", path=path)
        return self.git("cat-file", "blob", oid.decode()).stdout

    def receipt(self, request, **values):
        current = publication_status(self.root, request["operation_id"])
        current.update(values)
        write_json(self.base / "receipts" / (request["operation_id"] + ".json"), current)
        return current

    def requests(self):
        requests = []
        for file in (self.base / "operations").glob("*/request.json"):
            request = json.loads(file.read_text())
            operation = request.get("operation_id", "")
            if not OP_ID.fullmatch(operation) or file.parent.name != operation:
                raise IngestError("conflict", "Invalid publication operation")
            if request.get("state") != "pending":
                raise IngestError("conflict", "An ingestion is incomplete; resume it before publishing",
                                  operation_id=operation)
            if publication_status(self.root, operation)["state"] == "published":
                continue
            if not isinstance(request.get("changes"), dict) or not 1 <= len(request["changes"]) <= 25:
                raise IngestError("conflict", "Invalid publication manifest")
            for path, change in request["changes"].items():
                path_for(self.root, path)
                ignored = self.git("check-ignore", "--no-index", "-q", "--", path, check=False,
                                   env={"GIT_LITERAL_PATHSPECS": "0"}).returncode
                if ignored not in (0, 1):
                    raise GitFailure("check-ignore")
                if ignored == 0:
                    raise IngestError("conflict", "An ingestion path is ignored by Git; publication needs review", path=path)
                for field in ("before", "after"):
                    value = change.get(field)
                    if value is not None and not HEX.fullmatch(value):
                        raise IngestError("conflict", "Invalid snapshot checksum")
                if change["after"] is not None:
                    self.blob(request, change["after"])
            for path, checksum in request.get("dependencies", {}).items():
                path_for(self.root, path)
                if not HEX.fullmatch(checksum):
                    raise IngestError("conflict", "Invalid dependency checksum")
            requests.append(request)
        return sorted(requests, key=lambda r: (r["sequence"], r["operation_id"]))

    def blob(self, request, checksum):
        if not HEX.fullmatch(checksum):
            raise IngestError("conflict", "Invalid snapshot checksum")
        file = self.base / "operations" / request["operation_id"] / "blobs" / checksum
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 2_000_000:
            raise IngestError("conflict", "Publication snapshot is missing or invalid")
        content = file.read_bytes()
        if sha(content) != checksum:
            raise IngestError("conflict", "Publication snapshot checksum mismatch")
        content.decode("utf-8")
        return content

    def _snapshot_current(self, requests):
        """Check the latest version, including chains of administrative edits."""
        final = {}
        known = {}
        for request in requests:
            for path, change in request["changes"].items():
                if path in final and final[path] != change["before"]:
                    raise IngestError("conflict", "Publication operations do not form a continuous history", path=path)
                final[path] = change["after"]
                known.setdefault(path, set()).update((change["before"], change["after"]))
        for path, expected in final.items():
            target = path_for(self.root, path)
            actual = sha(target.read_bytes()) if target.exists() else None
            if actual != expected:
                raise IngestError("conflict", "File changed outside the approved ingestion", path=path)
            # Preserve another user's staged changes, even in approved paths.
            staged = self.git("show", ":" + path, check=False)
            checksum = sha(staged.stdout) if staged.returncode == 0 else None
            if checksum not in known[path]:
                head = self.tree_value("HEAD", path)
                if checksum != (sha(head) if head is not None else None):
                    raise IngestError("conflict", "Unrelated staged note changes require review", path=path)

    def _set_index(self, index_env, path, content):
        if content is None:
            self.git("update-index", "--force-remove", "--", path, env=index_env)
        else:
            oid = self.git("hash-object", "-w", "--stdin", data=content).stdout.decode().strip()
            self.git("update-index", "--add", "--cacheinfo", "100644", oid, path, env=index_env)

    def _save(self, request):
        ref = "refs/daedalus/ingest/" + request["operation_id"]
        head = self.oid("HEAD")
        saved = self.oid(ref)
        if saved:
            if not self.ancestor(saved, head):
                parent = self.oid(saved + "^")
                if head != parent:
                    raise IngestError("conflict", "Checkout moved after a preserved ingestion")
                self.git("update-ref", "refs/heads/main", saved, head)
            self.receipt(request, state="saved", commit=saved, error=None)
            return saved
        for path, expected in request.get("dependencies", {}).items():
            content = self.tree_value(head, path)
            if content is None or sha(content) != expected:
                raise IngestError("conflict", "Covered/legacy targets must already be versioned as reviewed", path=path)
        with tempfile.TemporaryDirectory(prefix="daedalus-index-") as temporary:
            environment = {"GIT_INDEX_FILE": str(Path(temporary) / "index")}
            self.git("read-tree", head, env=environment)
            for path, change in request["changes"].items():
                old = self.tree_value(head, path)
                actual = sha(old) if old is not None else None
                if actual != change["before"] and not (actual is None and change.get("allow_untracked")):
                    raise IngestError("conflict", "Git base differs from the reviewed note", path=path)
                content = self.blob(request, change["after"]) if change["after"] else None
                self._set_index(environment, path, content)
            tree = self.git("write-tree", env=environment).stdout.decode().strip()
        if tree == self.oid(head + "^{tree}"):
            saved = head
        else:
            message = "ingest: " + request["operation_id"] + "\n\nDaedalus-Operation: " + request["operation_id"] + "\n"
            saved = self.git("commit-tree", tree, "-p", head, data=message.encode()).stdout.decode().strip()
        # The private ref is a durable recovery point before HEAD moves.
        self.git("update-ref", ref, saved)
        if saved != head:
            self.git("update-ref", "refs/heads/main", saved, head)
        self.receipt(request, state="saved", commit=saved, error=None)
        return saved

    def changed(self, older, newer, *paths):
        args = ["diff", "--no-renames", "--name-only", "-z", older, newer]
        if paths:
            args += ["--", *paths]
        return set(self.git(*args).stdout.decode().strip("\0").split("\0")) - {""}

    def fetch(self):
        self.git("fetch", "--no-tags", "origin", "refs/heads/main:refs/remotes/origin/main")
        return self.oid("refs/remotes/origin/main")

    def _candidate(self, head, remote, allowed, dependencies, approved_commits):
        base = self.git("merge-base", head, remote).stdout.decode().strip()
        outgoing = set(self.git("rev-list", base + ".." + head).stdout.decode().split())
        if outgoing - approved_commits:
            raise IngestError("conflict", "Unpublished commits outside the ingestion journal require review")
        if self.changed(base, head) - allowed:
            raise IngestError("conflict", "Unpublished changes outside approved ingestions require review")
        if self.ancestor(remote, head):
            return head
        overlap = self.changed(base, remote, "wiki", "raw") & (allowed | dependencies)
        if overlap:
            raise IngestError("conflict", "The computer and server changed the same knowledge files",
                              paths=sorted(overlap))
        with tempfile.TemporaryDirectory(prefix="daedalus-merge-") as temporary:
            tree = Path(temporary) / "checkout"
            self.git("worktree", "add", "--detach", str(tree), head)
            try:
                result = self.git("merge", "--no-edit", remote, cwd=tree, check=False)
                if result.returncode:
                    raise IngestError("conflict", "Integration needs review; live files were preserved")
                return self.git("rev-parse", "HEAD", cwd=tree).stdout.decode().strip()
            finally:
                # Only the disposable integration copy is removed, never notes
                # or snapshots in the live checkout/publication directory.
                self.git("worktree", "remove", "--force", str(tree))

    def run(self, *, maintenance=False):
        with coordination(self.root, maintenance=maintenance, nonblocking=True):
            return self._run_locked()

    def _run_locked(self):
        if self.git("symbolic-ref", "--short", "HEAD").stdout.strip() != b"main":
            raise IngestError("conflict", "Automatic publication is only allowed from the server main checkout")
        requests = self.requests()
        if not requests:
            return {"state": "idle", "new_publication": False, "pushed": False, "operations": []}
        try:
            # A successful push may outlive its receipt (or a human may merge
            # the preserved commit while resolving a conflict). Acknowledge
            # ancestry first, before rejecting subsequently edited live notes.
            acknowledged = []
            if any(self.oid("refs/daedalus/ingest/" + r["operation_id"]) for r in requests):
                try:
                    remote = self.fetch()
                except GitFailure:
                    remote = None  # Still preserve new operations while offline.
                if remote:
                    remaining = []
                    for request in requests:
                        saved = self.oid("refs/daedalus/ingest/" + request["operation_id"])
                        if saved and self.ancestor(saved, remote):
                            self.receipt(request, state="published", commit=saved,
                                         published_commit=saved, error=None)
                            acknowledged.append(request["operation_id"])
                        else:
                            remaining.append(request)
                    requests = remaining
            if not requests:
                return {"state": "published", "new_publication": True, "pushed": False,
                        "operations": acknowledged}
            self._snapshot_current(requests)
            for request in requests:
                self._save(request)
            # Refresh only approved index entries. Other staged changes survive.
            # Repeating this after a crash repairs an interrupted index refresh.
            head = self.oid("HEAD")
            allowed = {p for r in requests for p in r["changes"]}
            dependencies = {p for r in requests for p in r.get("dependencies", {})}
            approved_commits = {self.oid("refs/daedalus/ingest/" + r["operation_id"]) for r in requests}
            for path in sorted(allowed):
                self._set_index({}, path, self.tree_value(head, path))
            pushed = False
            for _ in range(self.attempts):
                remote = self.fetch()
                if self.ancestor(head, remote):
                    published = head  # Handles a push whose successful reply was lost.
                    break
                candidate = self._candidate(head, remote, allowed, dependencies, approved_commits)
                result = self.git("push", "origin", candidate + ":refs/heads/main", check=False)
                if result.returncode == 0:
                    published = candidate
                    pushed = True
                    break
            else:
                raise GitFailure("push")
            for request in requests:
                self.receipt(request, state="published", published_commit=published, error=None)
            return {"state": "published", "new_publication": True, "pushed": pushed, "commit": published,
                    "operations": acknowledged + [r["operation_id"] for r in requests]}
        except IngestError as exc:
            for request in requests:
                self.receipt(request, state="conflict" if exc.code == "conflict" else "pending",
                             error=exc.result())
            raise
