#!/usr/bin/env python3
"""Explicit model download. No vault content is read or sent to the provider."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

MODELS = {
    "e5-small": {"repository": "Xenova/multilingual-e5-small", "max_length": 512,
                 "query_prefix": "query: ", "passage_prefix": "passage: ", "license": "MIT", "kind": "embedding"},
    "minilm": {"repository": "Xenova/paraphrase-multilingual-MiniLM-L12-v2", "max_length": 128,
               "query_prefix": "", "passage_prefix": "", "license": "Apache-2.0", "kind": "embedding"},
    "reranker": {"repository": "SugoLabs/mmarco-mMiniLMv2-L12-H384-v1", "max_length": 512,
                 "license": "Apache-2.0", "kind": "reranker"},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=MODELS)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--revision", default="main", help="Resolve once, then record the exact commit in model.json")
    args = parser.parse_args()
    from huggingface_hub import HfApi, hf_hub_download
    spec = dict(MODELS[args.model])
    info = HfApi().model_info(spec["repository"], revision=args.revision)
    spec["revision"] = info.sha
    spec["onnx_file"] = "onnx/model_quantized.onnx"
    # Temporary download and atomic completion marker; incomplete directories
    # cannot be loaded as a validated model by the server.
    args.directory.mkdir(parents=True, exist_ok=True)
    files = {}
    for filename in ("tokenizer.json", "onnx/model_quantized.onnx"):
        source = hf_hub_download(spec["repository"], filename, revision=info.sha,
                                 cache_dir=str(args.directory / ".download"))
        destination = args.directory / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        files[filename] = hashlib.sha256(destination.read_bytes()).hexdigest()
    spec["files"] = files
    staging = args.directory / "model.json.tmp"
    staging.write_text(json.dumps(spec, indent=2) + "\n")
    os.replace(staging, args.directory / "model.json")
    print(json.dumps(spec, indent=2))


if __name__ == "__main__":
    main()
