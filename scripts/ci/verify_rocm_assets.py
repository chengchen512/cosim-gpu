# SPDX-License-Identifier: Apache-2.0

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from ci_lifecycle import Lifecycle
from rocm_assets import PRODUCTS, build, inputs, verify


def check(output: Path) -> None:
    manifest = json.loads((output / "manifest.json").read_text())
    with Lifecycle().installed() as lifecycle:
        build(output, manifest["disk"]["format"], lifecycle)
        variable = "PKR_VAR_kernel_release"
        previous = os.environ.get(variable)
        try:
            os.environ[variable] = (
                "6.8.0-147-generic"
                if manifest["kernel_release"] != "6.8.0-147-generic"
                else "6.8.0-124-generic"
            )
            try:
                build(output, manifest["disk"]["format"], lifecycle)
            except ValueError as error:
                if "inputs differ" not in str(error):
                    raise
            else:
                raise AssertionError("a different kernel reused the image")
        finally:
            if previous is None:
                os.environ.pop(variable, None)
            else:
                os.environ[variable] = previous
    other_format = "raw" if manifest["disk"]["format"] == "qcow2" else "qcow2"
    try:
        verify(output, inputs(other_format))
    except ValueError as error:
        if "inputs differ" not in str(error):
            raise
    else:
        raise AssertionError("an image for different build inputs was accepted")

    with tempfile.TemporaryDirectory(
        prefix="image-integrity-", dir=output.parent
    ) as name:
        directory = Path(name)
        for product in (*PRODUCTS, "manifest.json"):
            if product == "kernel":
                shutil.copy2(output / product, directory / product)
            else:
                os.link(output / product, directory / product)
        with (directory / "kernel").open("r+b") as stream:
            stream.truncate((directory / "kernel").stat().st_size - 1)
        try:
            verify(directory)
        except ValueError as error:
            if "checksum mismatch: kernel" not in str(error):
                raise
        else:
            raise AssertionError("a truncated paired kernel was accepted")
    print(json.dumps({"status": "PASS", "input_key": manifest["input_key"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check integrity gates using a real built ROCm image"
    )
    parser.add_argument("output", type=Path)
    check(parser.parse_args().output.resolve())
