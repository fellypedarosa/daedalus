"""Complete remote/local ingestion with real MCP transports and synthetic notes."""
from __future__ import annotations

import asyncio
import json
import os
import runpy
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from starlette.testclient import TestClient

from tests.ingest.test_workflow import NEW_NODE, SOURCE, SOURCE_PATH, node, proposal
from daedalus_ingest import apply as application

ROOT = Path(__file__).resolve().parents[2]


def setup(base):
    root = base / "vault"
    (root / "raw/local").mkdir(parents=True)
    (root / "wiki/Concepts").mkdir(parents=True)
    (root / SOURCE_PATH).write_text(SOURCE)
    for path, content in (("wiki/index.md", "# Catalog\n\n## Pages\n"),
                          ("wiki/log.md", "# Log\n"), ("wiki/Ingestion_Tracker.md", "# Tracker\n")):
        (root / path).write_text(content)
    return root, {"DAEDALUS_VAULT_DIR": str(root), "DAEDALUS_INDEX_DIR": str(base / "index"),
                  "DAEDALUS_INGEST_DIR": str(base / "ingest"), "DAEDALUS_INDEX_INTERVAL": "0",
                  "DAEDALUS_SYNC_DIR": str(root / ".mcp/.daedalus-sync"),
                  "DAEDALUS_MODEL_DIR": "", "DAEDALUS_RERANKER_DIR": ""}


def unpack(content):
    return json.loads("\n".join(item.text for item in content.content if item.type == "text"))


class StdioIngestTests(unittest.IsolatedAsyncioTestCase):
    async def test_raw_upload_is_separate_from_ingestion_and_survives_client_reconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, environment = setup(base)
            before = {p: p.read_bytes() for p in root.rglob("*.md")}
            args = {"category": "clipper", "filename": "Minha nota.md", "content": "# Café\r\nOriginal.\r\n"}
            def transport():
                return StdioTransport(command=sys.executable, args=[str(ROOT / "daedalus_mcp.py")],
                    env={**os.environ, **environment}, cwd=str(base), log_file=base / "capture.log")
            async with Client(transport(), timeout=40) as client:
                reply = unpack(await client.call_tool("create_raw_note", args))
                self.assertEqual(reply["state"], "saved")
                self.assertEqual(reply["publication"]["state"], "pending")
                self.assertFalse(reply["ingestion_requested"])
                self.assertEqual((root / reply["path"]).read_bytes(), args["content"].encode())
                sources = unpack(await client.call_tool("ingest_sources"))
                self.assertIn(reply["path"], [s["path"] for s in sources["sources"]])
                self.assertTrue(all(p.read_bytes() == data for p, data in before.items()))
            async with Client(transport(), timeout=40) as client:
                repeated = unpack(await client.call_tool("create_raw_note", args))
                self.assertEqual(repeated["operation_id"], reply["operation_id"])
                self.assertTrue(repeated["reused"])
                status = unpack(await client.call_tool("ingest_status", {"operation_id": reply["operation_id"]}))
                self.assertEqual(status["kind"], "raw_note")
                self.assertEqual(status["publication"]["state"], "pending")

    async def test_entire_ingestion_without_direct_client_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, environment = setup(base)
            transport = StdioTransport(command=sys.executable, args=[str(ROOT / "daedalus_mcp.py")],
                env={**os.environ, **environment}, cwd=str(base), log_file=base / "server.log")
            async with Client(transport, timeout=40) as client:
                sources = unpack(await client.call_tool("ingest_sources"))
                self.assertEqual(sources["sources"][0]["path"], SOURCE_PATH)
                prepared = unpack(await client.call_tool("ingest_prepare", {"source_path": SOURCE_PATH, "request_id": "stdio-pilot"}))
                self.assertEqual(prepared["text"], SOURCE)
                review = unpack(await client.call_tool("ingest_preview", {
                    "operation_id": prepared["operation_id"], "proposal": proposal()}))
                self.assertEqual(review["state"], "validated")
                self.assertFalse((root / NEW_NODE).exists())
                result = unpack(await client.call_tool("ingest_apply", {
                    "operation_id": prepared["operation_id"], "proposal_digest": review["proposal_digest"]}))
                self.assertEqual(result["state"], "committed")
                self.assertEqual(result["publication"]["state"], "pending")
                for _ in range(40):
                    status = unpack(await client.call_tool("ingest_status", {"operation_id": prepared["operation_id"]}))
                    if status["search_state"] == "search_ready":
                        break
                    await asyncio.sleep(.05)
                self.assertEqual(status["search_state"], "search_ready")
                search = unpack(await client.call_tool("search", {"query": "outbound tunnel", "output": "json"}))
                self.assertIn(NEW_NODE, [r["path"] for r in search["results"]])
                self.assertEqual((root / NEW_NODE).read_text(), node())


class HttpIngestTests(unittest.TestCase):
    def test_token_permissions_full_flow_and_other_client_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, environment = setup(base)
            tokens = base / "tokens.json"
            tokens.write_text(json.dumps({"tokens": [
                {"id": "reader", "token": "<SYNTHETIC_READER>", "active": True, "scopes": ["daedalus:read"]},
                {"id": "legacy", "token": "<SYNTHETIC_LEGACY>", "active": True},
                {"id": "writer", "token": "<SYNTHETIC_WRITER>", "active": True, "scopes": ["daedalus:ingest"]},
                {"id": "other", "token": "<SYNTHETIC_OTHER>", "active": True, "scopes": ["daedalus:ingest"]},
            ]}))
            environment.update(DAEDALUS_TOKENS_FILE=str(tokens), DAEDALUS_AUDIT_LOG=str(base / "access.jsonl"))
            def exercise(app, **kwargs):
                with TestClient(app) as http:
                    def call(name, args=None, credential="<SYNTHETIC_WRITER>"):
                        response = http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                            "params": {"name": name, "arguments": args or {}}}, headers={
                            "Accept": "application/json, text/event-stream", "Authorization": "Bearer " + credential})
                        self.assertEqual(response.status_code, 200, response.text)
                        try:
                            result = response.json()
                        except ValueError:
                            result = json.loads(next(line[6:] for line in response.text.splitlines() if line.startswith("data: ")))
                        self.assertNotIn("error", result, result)
                        text = "\n".join(item["text"] for item in result["result"]["content"] if item["type"] == "text")
                        try:
                            return json.loads(text)
                        except ValueError:
                            return text
                    for credential in ("<SYNTHETIC_READER>", "<SYNTHETIC_LEGACY>"):
                        self.assertEqual(call("ingest_sources", credential=credential)["sources"][0]["path"], SOURCE_PATH)
                        rejected = call("ingest_prepare", {"source_path": SOURCE_PATH, "request_id": "denied"}, credential)
                        self.assertEqual(rejected["state"], "forbidden")
                        for name, args in (("create_raw_note", {"category": "clipper", "filename": "Denied.md", "content": "No write"}),
                            ("save_raw_ai_memory", {"title": "Denied", "content": "No write"}),
                            ("update_wiki_index", {"node_path": NEW_NODE, "description": "Denied"}),
                            ("auto_catalog_ai_memory", {"source_filename": SOURCE_PATH, "nodes_created": [], "nodes_expanded": []})):
                            denied = call(name, args, credential)
                            self.assertTrue("explicit" in str(denied) or denied.get("state") == "forbidden")
                    captured = call("create_raw_note", {"category": "clipper", "filename": "Upload.md", "content": "# Original\n"})
                    self.assertEqual(captured["state"], "saved")
                    self.assertEqual(captured["publication"]["state"], "pending")
                    self.assertEqual(call("ingest_status", {"operation_id": captured["operation_id"]})["state"], "saved")
                    self.assertEqual(call("ingest_status", {"operation_id": captured["operation_id"]}, "<SYNTHETIC_OTHER>")["state"], "forbidden")
                    self.assertEqual((root / "wiki/log.md").read_text(), "# Log\n")
                    prepared = call("ingest_prepare", {"source_path": SOURCE_PATH, "request_id": "http-pilot"})
                    rejected = call("ingest_status", {"operation_id": prepared["operation_id"]}, "<SYNTHETIC_OTHER>")
                    self.assertEqual(rejected["state"], "forbidden")
                    review = call("ingest_preview", {"operation_id": prepared["operation_id"], "proposal": proposal()})
                    self.assertFalse((root / NEW_NODE).exists())
                    # Recovery is reachable through MCP even before a search
                    # index exists; a partial operation must not require search.
                    with patch.object(application, "publish", side_effect=OSError("injected outage")):
                        interrupted = call("ingest_apply", {"operation_id": prepared["operation_id"],
                            "proposal_digest": review["proposal_digest"]})
                    self.assertEqual(interrupted["state"], "failed_recoverable")
                    self.assertFalse((base / "index/current.json").exists())
                    self.assertEqual(call("ingest_status", {"operation_id": prepared["operation_id"]})["state"],
                                     "failed_recoverable")
                    result = call("ingest_apply", {"operation_id": prepared["operation_id"], "proposal_digest": review["proposal_digest"]})
                    self.assertEqual(result["state"], "committed")
                    self.assertEqual(result["publication"]["state"], "pending")
                    for _ in range(40):
                        result = call("ingest_status", {"operation_id": prepared["operation_id"]})
                        if result["search_state"] == "search_ready":
                            break
                        time.sleep(.05)
                    self.assertEqual(result["search_state"], "search_ready")
                    self.assertIn(NEW_NODE, [r["path"] for r in call("search", {"query": "outbound tunnel", "output": "json"})["results"]])
                    # An already authenticated legacy token still cannot apply a preview.
                    rejected = call("ingest_apply", {"operation_id": prepared["operation_id"], "proposal_digest": review["proposal_digest"]}, "<SYNTHETIC_LEGACY>")
                    self.assertEqual(rejected["state"], "forbidden")
            with patch.dict(os.environ, environment), patch.object(sys, "argv", ["daedalus_mcp.py", "--sse"]), \
                 patch("uvicorn.run", side_effect=exercise):
                namespace = runpy.run_path(str(ROOT / "daedalus_mcp.py"), run_name="__main__")
            if namespace.get("_ENGINE"):
                namespace["_ENGINE"].close()
