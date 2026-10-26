"""Real MCP transports against an isolated synthetic vault, never the real notes."""
from __future__ import annotations

import asyncio
import contextlib
import io
import json
import os
import runpy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/search"


def message(result):
    return "\n".join(item.text for item in result.content if item.type == "text")


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_all_twelve_tools_and_compatible_search(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            vault = base / "vault"
            shutil.copytree(FIXTURE, vault)
            for area in ("clipper", "youtube", "ai"):
                (vault / "raw" / area).mkdir(exist_ok=True)
            transport = StdioTransport(command=sys.executable, args=[str(ROOT / "daedalus_mcp.py")],
                env={**os.environ, "DAEDALUS_VAULT_DIR": str(vault), "DAEDALUS_INDEX_DIR": str(base / "index"),
                     "DAEDALUS_INDEX_INTERVAL": "0", "DAEDALUS_MODEL_DIR": "", "DAEDALUS_RERANKER_DIR": "",
                     "DAEDALUS_INGEST_DIR": str(base / "ingest"),
                     "DAEDALUS_TEST_AUDIT_LOG": str(base / "test-audit.jsonl")},
                cwd=str(base), log_file=base / "server.log")
            async with Client(transport, timeout=30) as client:
                names = {tool.name for tool in await client.list_tools()}
                self.assertTrue({"search", "read", "list_nodes", "backlinks", "outlinks", "crawl", "audit", "summary",
                                 "test", "create_raw_note", "save_raw_ai_memory", "update_wiki_index", "auto_catalog_ai_memory",
                                 "ingest_sources", "ingest_prepare", "ingest_preview", "ingest_apply", "ingest_status"} <= names)
                proofs = [json.loads(message(await client.call_tool("test"))) for _ in range(2)]
                self.assertEqual(proofs[0]["session_id"], proofs[1]["session_id"])
                self.assertEqual(proofs[1]["call_number"], proofs[0]["call_number"] + 1)
                self.assertEqual(proofs[0]["status"], "MCP_CONNECTED")
                overview = json.loads(message(await client.call_tool("summary")))
                nodes = json.loads(message(await client.call_tool("list_nodes")))
                self.assertEqual(overview["total_nodes"], 7)
                self.assertEqual(nodes["total_nodes"], 7)
                self.assertTrue(all(h.get("path", "").startswith("wiki/") for h in overview["hub_nodes"]))
                self.assertIn("wiki/Other/Duplicate.md", nodes["domains"]["Other"])
                old_call = message(await client.call_tool("search", {"query": "D3cold", "limit": 2}))
                self.assertIn("wiki/Other/Drivers.md", old_call)
                result = json.loads(message(await client.call_tool("search", {
                    "query": "azimuth-raw-731", "mode": "exact", "output": "json"})))
                path = result["results"][0]["path"]
                self.assertEqual(path, "raw/ai/Tunnel_Source.md")
                self.assertIn("azimuth-raw-731", message(await client.call_tool("read", {"filepath": path})))
                self.assertIn("Ambiguous", message(await client.call_tool("read", {"filepath": "Duplicate"})))
                self.assertIn("not found", message(await client.call_tool("read", {"filepath": str(ROOT / "daedalus_mcp.py")})))
                outgoing = json.loads(message(await client.call_tool("outlinks", {"node_name": "Tunnels"})))
                self.assertTrue(any(r.get("path") == path for r in outgoing["outlinks"]))
                incoming = json.loads(message(await client.call_tool("backlinks", {"node_name": path})))
                self.assertIn("wiki/Networking/Tunnels.md", [r["path"] for r in incoming["backlinks"]])
                self.assertIn("azimuth-raw-731", message(await client.call_tool("crawl", {"node_name": path})))
                audit = json.loads(message(await client.call_tool("audit")))
                self.assertIn("Duplicate", audit["ambiguous_links"])
                await client.call_tool("save_raw_ai_memory", {"title": "Synthetic rule", "content": "# Rule\nSynthetic content.\n"})
                self.assertTrue((vault / "raw/ai/synthetic_rule.md").is_file())
                (vault / "wiki/Other/New.md").write_text("---\ntags: [test]\ndate_created: 2026-10-25\nsources:\n  - '[[raw/ai/synthetic_rule.md]]'\n---\n# Synthetic Rule\nAutor: [[LLM]]\n")
                await client.call_tool("update_wiki_index", {"node_path": "wiki/Other/New.md", "description": "Synthetic reference"})
                await client.call_tool("auto_catalog_ai_memory", {"source_filename": "synthetic_rule.md", "nodes_created": ["wiki/Other/New.md"], "nodes_expanded": []})
                self.assertTrue((vault / "raw/ai/cataloged/synthetic_rule.md").is_file())


class HTTPTests(unittest.TestCase):
    def test_invalid_auth_configuration_stops_before_http_start(self):
        active = {"id": "fixture", "token": "<SYNTHETIC_TEST_TOKEN>", "active": True}
        cases = {
            "missing": None,
            "directory": None,
            "unreadable": {"tokens": [active]},
            "malformed_json": '{"tokens":',
            "invalid_utf8": b'\xff',
            "invalid_root": [],
            "missing_list": {},
            "invalid_list": {"tokens": {}},
            "empty": {"tokens": []},
            "inactive": {"tokens": [{**active, "active": False}]},
            "invalid_entry": {"tokens": [None]},
            "invalid_active": {"tokens": [{**active, "active": "false"}]},
            "missing_id": {"tokens": [{"token": active["token"], "active": True}]},
            "empty_token": {"tokens": [{**active, "token": " "}]},
            "invalid_token": {"tokens": [{**active, "token": 42}]},
            "duplicate": {"tokens": [active, active]},
        }
        for name, data in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                tokens_file = base / "tokens.json"
                if name == "directory":
                    tokens_file.mkdir()
                elif data is not None:
                    if isinstance(data, bytes):
                        tokens_file.write_bytes(data)
                    else:
                        tokens_file.write_text(data if isinstance(data, str) else json.dumps(data))
                environment = {"DAEDALUS_VAULT_DIR": str(base),
                               "DAEDALUS_INDEX_DIR": str(base / "index"),
                               "DAEDALUS_TOKENS_FILE": str(tokens_file)}
                error = io.StringIO()
                permission = (patch.object(Path, "read_text", side_effect=PermissionError())
                              if name == "unreadable" else contextlib.nullcontext())
                with patch.dict(os.environ, environment), permission, \
                     patch.object(sys, "argv", ["daedalus_mcp.py", "--sse"]), \
                     patch("uvicorn.run") as serve, contextlib.redirect_stderr(error):
                    with self.assertRaises(SystemExit) as stopped:
                        runpy.run_path(str(ROOT / "daedalus_mcp.py"), run_name="__main__")
                self.assertEqual(stopped.exception.code, 1)
                serve.assert_not_called()
                self.assertFalse((base / "index").exists())
                self.assertIn("Autenticação obrigatória", error.getvalue())
                self.assertNotIn(active["token"], error.getvalue())

    def test_http_search_auth_alias_readiness_and_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            vault = base / "vault"
            shutil.copytree(FIXTURE, vault)
            tokens_file = base / "tokens.json"
            tokens_file.write_text(json.dumps({"tokens": [
                {"id": "fixture", "token": "<SYNTHETIC_TEST_TOKEN>", "active": True},
                {"id": "disabled", "token": "<SYNTHETIC_INACTIVE_TOKEN>", "active": False},
            ]}))
            environments = {"DAEDALUS_VAULT_DIR": str(vault), "DAEDALUS_INDEX_DIR": str(base / "index"),
                "DAEDALUS_INDEX_INTERVAL": "0", "DAEDALUS_MODEL_DIR": "", "DAEDALUS_RERANKER_DIR": "",
                "DAEDALUS_TOKENS_FILE": str(tokens_file), "DAEDALUS_AUDIT_LOG": str(base / "access.jsonl"),
                "DAEDALUS_INGEST_DIR": str(base / "ingest")}
            def exercise(app, **kwargs):
                with TestClient(app) as http:
                    self.assertEqual(http.get("/health").status_code, 200)
                    self.assertEqual(http.get("/ready").status_code, 200)
                    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                        "protocolVersion": "2025-03-26", "capabilities": {},
                        "clientInfo": {"name": "daedalus-test", "version": "1"}}}
                    accept = {"Accept": "application/json, text/event-stream"}
                    authorized = {**accept, "Authorization": "Bearer <SYNTHETIC_TEST_TOKEN>"}
                    rejected_headers = [accept,
                        {**accept, "Authorization": "Bearer <SYNTHETIC_INVALID_TOKEN>"},
                        {**accept, "Authorization": "Bearer <SYNTHETIC_INACTIVE_TOKEN>"}]
                    for route in ("/mcp", "/sse"):
                        for headers in rejected_headers:
                            for method in ("GET", "POST", "DELETE"):
                                with self.subTest(route=route, method=method, headers=headers):
                                    # Stateless /mcp does not expose GET; routing
                                    # rejects it before the authentication layer.
                                    expected = 405 if route == "/mcp" and method == "GET" else 401
                                    self.assertEqual(http.request(method, route, json=request,
                                                                 headers=headers).status_code, expected)
                        self.assertEqual(http.post(route, json=request, headers=authorized).status_code, 200)
                    request = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                        "name": "search", "arguments": {"query": "azimuth-raw-731", "mode": "exact", "output": "json"}}}
                    for route in ("/mcp", "/sse"):
                        for headers in rejected_headers:
                            response = http.post(route, json=request, headers=headers)
                            self.assertEqual(response.status_code, 401)
                            self.assertNotIn("azimuth-raw-731", response.text)
                        response = http.post(route, json=request, headers=authorized)
                        self.assertEqual(response.status_code, 200)
                        self.assertIn("raw/ai/Tunnel_Source.md", response.text)
                    (base / "index/current.json").write_text('{"file":"generation-missing.sqlite"}')
                    self.assertEqual(http.get("/ready").status_code, 503)
                    self.assertEqual(http.get("/health").status_code, 200)
            with patch.dict(os.environ, environments), patch.object(sys, "argv", ["daedalus_mcp.py", "--sse"]), patch("uvicorn.run", side_effect=exercise):
                namespace = runpy.run_path(str(ROOT / "daedalus_mcp.py"), run_name="__main__")
            if namespace.get("_ENGINE"):
                namespace["_ENGINE"].close()


if __name__ == "__main__":
    unittest.main()
