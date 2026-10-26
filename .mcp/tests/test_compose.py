"""Validate the local demonstration Compose without importing MCP dependencies."""
import json
import os
import shutil
import subprocess
import unittest
from daedalus_paths import APP_DIR, REPO_DIR


@unittest.skipUnless(shutil.which("docker"), "Docker Compose CLI is required")
class ComposeLayoutTests(unittest.TestCase):
    def config(self, path):
        env = {"PATH": os.defpath}
        r = subprocess.run([shutil.which("docker"), "compose", "--env-file", "/dev/null", "-f", str(path),
                            "config", "--format", "json"], env=env, cwd=REPO_DIR, check=True,
                           capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout)

    def test_compose_is_local_isolated_and_needs_no_env(self):
        canonical = self.config(APP_DIR / "docker-compose.yml")
        self.assertEqual(canonical["name"], "daedalus-public-demo")
        service = canonical["services"]["daedalus-mcp"]
        self.assertEqual(service["build"]["context"], str(APP_DIR))
        self.assertEqual(service["build"]["dockerfile"], "Dockerfile")
        mounts = {m["target"]: m for m in service["volumes"]}
        self.assertEqual(mounts["/vault/wiki"]["source"], str(APP_DIR / "tmp/demo-vault/wiki"))
        self.assertEqual(mounts["/vault/raw"]["source"], str(APP_DIR / "tmp/demo-vault/raw"))
        self.assertEqual(mounts["/var/lib/daedalus-sync"]["type"], "volume")
        self.assertEqual(mounts["/run/daedalus/tokens.json"]["source"], str(APP_DIR / "tokens.json"))
        self.assertTrue(mounts["/models"]["read_only"])
        self.assertNotIn("container_name", service)
        self.assertFalse(service.get("labels"))
        self.assertEqual(service["ports"][0]["host_ip"], "127.0.0.1")
        self.assertEqual(service["ports"][0]["target"], 8000)
        self.assertTrue(all(not n.get("external") for n in canonical.get("networks", {}).values()))
        self.assertTrue(all(v["name"].startswith(canonical["name"] + "_")
                            and not v.get("external") for v in canonical["volumes"].values()))
