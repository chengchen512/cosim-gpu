# SPDX-License-Identifier: Apache-2.0

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from runtime_artifact import ARCHIVES, reuse, verify_payload


def check(source: Path, publication: Path) -> None:
    original = json.loads((source / "manifest.json").read_text())
    published = json.loads((publication / "manifest.json").read_text())
    verify_payload(publication, published)
    for field in (
        "build_source", "build_run", "build_attempt", "build_key",
        "image_id", "files",
    ):
        if published[field] != original[field]:
            raise AssertionError(f"publication changed original {field}")
    image = original["image"]
    with tempfile.TemporaryDirectory(
        prefix="gem5-integrity-", dir=source.parent
    ) as name:
        directory = Path(name)
        previous = os.environ.get("COSIM_GEM5_CACHE_EPOCH")
        try:
            os.environ["COSIM_GEM5_CACHE_EPOCH"] = (
                os.environ.get("COSIM_GEM5_CACHE_EPOCH", "1") + "-check"
            )
            try:
                reuse(source, directory / "different-inputs", image)
            except ValueError as error:
                if "build_key" not in str(error):
                    raise
            else:
                raise AssertionError("different build inputs reused the cache")
        finally:
            if previous is None:
                os.environ.pop("COSIM_GEM5_CACHE_EPOCH", None)
            else:
                os.environ["COSIM_GEM5_CACHE_EPOCH"] = previous
        invalid = directory / "invalid"
        invalid.mkdir()
        for filename in (*ARCHIVES, "manifest.json"):
            if filename == "libvfio-user.a.gz":
                shutil.copy2(source / filename, invalid / filename)
            else:
                os.link(source / filename, invalid / filename)
        library = invalid / "libvfio-user.a.gz"
        with library.open("r+b") as stream:
            stream.truncate(library.stat().st_size - 1)
        destination = directory / "invalid-publication"
        try:
            reuse(invalid, destination, image)
        except ValueError as error:
            if "checksum mismatch" not in str(error):
                raise
        else:
            raise AssertionError("a corrupted library was accepted")
        if destination.exists():
            raise AssertionError("corrupt inputs published a partial artifact")
    print(json.dumps({"status": "PASS", "build_key": original["build_key"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify cache gates with real gem5 build artifacts"
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("publication", type=Path)
    args = parser.parse_args()
    check(args.source.resolve(), args.publication.resolve())
