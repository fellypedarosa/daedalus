"""Synthetic vector contracts plus opt-in evaluation of a real, offline model."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
import threading

try:
    import numpy as np
except ImportError:
    np = None

from daedalus_search.engine import SearchEngine
from daedalus_search.models import Candidate, Passage, digest
from daedalus_search.semantic import LocalEncoder, LocalReranker


class FakeEncoder:
    identity = "synthetic-vector-contract-v1"
    spec = {"kind": "test-only"}
    max_length = 512
    np = np
    calls = 0

    def count_tokens(self, text):
        return len(text.split())

    def passage_input(self, document, passage):
        return document.title + " " + passage.text

    def encode(self, texts, query=False):
        self.calls += len(texts)
        vectors = np.array([[1, .2] if "tunnel" in t.casefold() else [.2, 1] for t in texts], dtype=np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


@unittest.skipIf(np is None, "Install requirements-search.txt for vector contract tests")
class VectorContractTests(unittest.TestCase):
    def test_interrupted_build_reuses_durable_vectors_without_publishing_partial_index(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            shutil.copytree(Path(__file__).resolve().parents[1] / "fixtures/search", base / "vault")
            engine = SearchEngine(base / "vault", base / "index", interval=0)
            encoder = FakeEncoder()
            original = encoder.encode
            batches = []
            def interrupted(texts, query=False):
                if batches:
                    raise RuntimeError("interrupted after first durable batch")
                batches.append(texts)
                return original(texts, query)
            encoder.encode = interrupted
            engine.encoder = encoder
            with self.assertRaises(RuntimeError):
                engine.reindex()
            self.assertFalse((base / "index/current.json").exists())
            encoder.encode = original
            result = engine.reindex()
            self.assertGreaterEqual(result["reused_embeddings"], 8)
            self.assertTrue(engine.status()["ready"])
            engine.close()

    def test_failed_reranking_does_not_partially_mutate_retrieval_scores(self):
        model = object.__new__(LocalReranker)
        model.lock, model.np = threading.Lock(), np
        calls = []
        def run(text):
            if calls:
                raise ValueError("oversized second pair")
            calls.append(text)
            return [np.array([12.])], {}
        model._run = run
        passages = [Passage(str(i), f"wiki/{i}.md", "", 1, 1, str(i), str(i)) for i in range(2)]
        candidates = [Candidate(p, .01, {"lexical"}) for p in passages]
        with self.assertRaises(ValueError):
            model.rank("query", candidates)
        self.assertEqual([c.score for c in candidates], [.01, .01])
        self.assertTrue(all(c.channels == {"lexical"} for c in candidates))

    def test_cache_model_change_and_semantic_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            shutil.copytree(Path(__file__).resolve().parents[1] / "fixtures/search", base / "vault")
            engine = SearchEngine(base / "vault", base / "index", interval=0)
            engine.encoder = FakeEncoder()
            first = engine.reindex()
            self.assertGreater(first["embedded"], 0)
            count = engine.encoder.calls
            same = engine.reindex()
            self.assertTrue(same["unchanged"])
            self.assertEqual(engine.encoder.calls, count)
            path = base / "vault/raw/ai/Isolated.md"
            path.write_text(path.read_text() + "\nExtra synthetic fact.\n")
            updated = engine.reindex()
            self.assertGreater(updated["reused_embeddings"], 0)
            self.assertEqual(engine.search("tunnel")["retrieval"], "hybrid")
            original_encode = engine.encoder.encode
            engine.encoder.encode = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("synthetic failure"))
            result = engine.search("NAT")
            self.assertEqual(result["retrieval"], "lexical")
            self.assertTrue(any("semantic_unavailable" in w for w in result["warnings"]))
            engine.encoder.encode = original_encode
            engine.encoder.identity = "changed-model-contract"
            changed = engine.reindex()
            self.assertEqual(changed["reused_embeddings"], 0)
            engine.close()
            second = SearchEngine(base / "vault", base / "index", interval=0)
            second.encoder = engine.encoder
            second.prepare()
            self.assertEqual(second.status()["retrieval"], "hybrid")
            second.close()


@unittest.skipUnless(os.environ.get("DAEDALUS_TEST_MODEL_DIR"), "Opt in to real-model tests with DAEDALUS_TEST_MODEL_DIR")
class RealModelTests(unittest.TestCase):
    def test_offline_multilingual_model_and_checksum_verification(self):
        model_dir = Path(os.environ["DAEDALUS_TEST_MODEL_DIR"])
        encoder = LocalEncoder(model_dir)
        vector = encoder.encode(["Como acessar um serviço atrás de NAT?"], query=True)
        self.assertEqual(vector.shape[0], 1)
        self.assertTrue(encoder.np.isfinite(vector).all())
        with self.assertRaises(ValueError):
            encoder.encode(["word " * 10000])
        with tempfile.TemporaryDirectory() as tampered:
            invalid = Path(tampered)
            spec = dict(encoder.spec)
            spec["files"] = {**encoder.spec["files"], "tokenizer.json": "0" * 64}
            (invalid / "tokenizer.json").write_text("{}")
            (invalid / "model.json").write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                LocalEncoder(invalid)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            shutil.copytree(Path(__file__).resolve().parents[1] / "fixtures/search", base / "vault")
            engine = SearchEngine(base / "vault", base / "index", interval=0)
            engine.encoder = encoder
            engine.reindex()
            result = engine.search("How can I expose a local application behind a router?", scope="wiki")
            self.assertEqual(result["retrieval"], "hybrid")
            self.assertIn("wiki/Networking/Tunnels.md", [r["path"] for r in result["results"]])
            engine.close()
