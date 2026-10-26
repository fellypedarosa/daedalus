"""Offline ONNX inference. Only the explicit preparation script uses network."""
from __future__ import annotations

import json
import threading
from pathlib import Path

from .models import Candidate, digest


class LocalEncoder:
    kind = "embedding"

    def __init__(self, directory: Path, threads: int = 2):
        directory = directory.resolve()
        self.spec = json.loads((directory / "model.json").read_text())
        if self.spec.get("kind") != self.kind:
            raise ValueError("Model kind does not match its retrieval role")
        if not {"tokenizer.json", self.spec["onnx_file"]}.issubset(self.spec["files"]):
            raise ValueError("All inference artifacts must have recorded checksums")
        self.identity = digest(json.dumps(self.spec, sort_keys=True))
        for name, expected in self.spec["files"].items():
            path = (directory / name).resolve()
            if not path.is_relative_to(directory) or digest(path.read_bytes()) != expected:
                raise ValueError("Model artifact checksum mismatch")
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        ort.disable_telemetry_events()
        self.np = np
        self.max_length = int(self.spec["max_length"])
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.no_truncation()
        pad = self.tokenizer.token_to_id("[PAD]")
        if pad is None:
            pad = self.tokenizer.token_to_id("<pad>")
        self.tokenizer.enable_padding(pad_id=pad or 0)
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(directory / self.spec["onnx_file"]),
                                           sess_options=options, providers=["CPUExecutionProvider"])
        self.lock = threading.Lock()
        self.inputs = {v.name for v in self.session.get_inputs()}

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False).ids)

    def _run(self, texts):
        encodings = self.tokenizer.encode_batch(texts)
        if any(len(e.ids) > self.max_length for e in encodings):
            raise ValueError("Input exceeds model context; segmentation must preserve all tokens")
        np = self.np
        values = {"input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
                  "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
                  "token_type_ids": np.array([e.type_ids for e in encodings], dtype=np.int64)}
        return self.session.run(None, {k: v for k, v in values.items() if k in self.inputs}), values

    def encode(self, texts: list[str], query: bool = False):
        prefix = self.spec.get("query_prefix" if query else "passage_prefix", "")
        arrays = []
        with self.lock:
            for start in range(0, len(texts), 8):
                output, values = self._run([prefix + t for t in texts[start:start + 8]])
                hidden = output[0]
                if hidden.ndim == 3:
                    mask = values["attention_mask"][..., None]
                    vectors = (hidden * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1)
                else:
                    vectors = hidden
                vectors = vectors.astype(self.np.float32)
                vectors /= self.np.linalg.norm(vectors, axis=1, keepdims=True).clip(min=1e-12)
                if not self.np.isfinite(vectors).all():
                    raise ValueError("Non-finite embeddings")
                arrays.append(vectors)
        return self.np.concatenate(arrays) if arrays else self.np.empty((0, 0), dtype=self.np.float32)

    def passage_input(self, document, passage) -> str:
        context = document.title + "\n" + passage.section
        # Context is metadata, not evidence. Bound it before adding the literal
        # passage, which is never silently truncated.
        while self.count_tokens(context) > 24:
            context = context[:max(1, len(context) * 3 // 4)]
        return context + "\n" + passage.text


class SemanticSearch:
    def __init__(self, encoder, connection):
        self.encoder = encoder
        np = encoder.np
        rows = connection.execute("SELECT passage_id, vector, dimension FROM embeddings WHERE model=? ORDER BY passage_id",
                                  (encoder.identity,)).fetchall()
        self.ids = [row["passage_id"] for row in rows]
        self.matrix = np.stack([np.frombuffer(row["vector"], dtype="<f4", count=row["dimension"]) for row in rows]) if rows else None
        self._query = None
        self._vector = None

    def search(self, query, passages, scope="all", limit=30, paths=None):
        if self.matrix is None:
            return []
        if query != self._query:
            self._vector = self.encoder.encode([query], query=True)[0]
            self._query = query
        vector = self._vector
        scores = self.matrix @ vector
        np = self.encoder.np
        eligible = [i for i, pid in enumerate(self.ids) if pid in passages
                    and (scope == "all" or passages[pid].path.startswith(scope + "/"))
                    and (paths is None or passages[pid].path in paths)]
        ordered = sorted(eligible, key=lambda i: (-float(scores[i]), self.ids[i]))[:limit]
        return [Candidate(passages[self.ids[i]], float(scores[i]), {"semantic"}) for i in ordered]


class LocalReranker(LocalEncoder):
    kind = "reranker"

    def rank(self, query: str, candidates: list[Candidate]) -> list[Candidate]:
        ranked = []
        with self.lock:
            for candidate in candidates:
                output, _ = self._run([(query, candidate.passage.text)])
                score = float(output[0].reshape(-1)[-1])
                if not self.np.isfinite(score):
                    raise ValueError("Non-finite reranker score")
                ranked.append(Candidate(candidate.passage, score, candidate.channels | {"reranker"}, list(candidate.via)))
        return sorted(ranked, key=lambda c: (-c.score, c.passage.id))
