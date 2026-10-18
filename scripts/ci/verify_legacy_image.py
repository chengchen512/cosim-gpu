# SPDX-License-Identifier: Apache-2.0

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import uuid

from ci_lifecycle import Lifecycle
from runtime_artifact import ROOT, sha256


def check(output: Path) -> None:
    token = uuid.uuid4().hex
    image = f"cosim-build-preflight-{token}:missing"
    build_dir = Path("build") / f"image-preflight-{token}" / "VEGA_X86"
    directory = output / f"legacy-image-{token}"
    directory.mkdir(parents=True)
    script = ROOT / "scripts/host/run_mi300x_fs.sh"
    environment = {
        **os.environ, "COSIM_ENV": "host", "GEM5_RUN_IMAGE": image,
        "GEM5_BUILD_DIR": str(build_dir),
    }
    with Lifecycle().installed() as lifecycle:
        with (directory / "output.log").open("wb") as log:
            with subprocess.Popen(
                ["bash", str(script), "build-gem5"], cwd=ROOT,
                env=environment, stdin=subprocess.DEVNULL, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True,
            ) as process:
                with lifecycle.own(process):
                    try:
                        status = process.wait(timeout=30)
                        lifecycle.check()
                    finally:
                        if (process.poll() is None
                                or lifecycle.reason is not None):
                            try:
                                os.killpg(process.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            process.wait()
    output_text = (directory / "output.log").read_text()
    if status == 0 or f"dev.sh: image {image} is missing" not in output_text:
        raise AssertionError(
            f"selected image preflight failed; see {directory}"
        )
    if (ROOT / "gem5" / build_dir).exists():
        raise AssertionError("the build started before image preflight")
    verdict = {
        "status": "PASS", "selected_image": image,
        "script_sha256": sha256(script), "artifact_directory": str(directory),
    }
    (directory / "verdict.json").write_text(
        json.dumps(verdict, indent=2) + "\n"
    )
    print(json.dumps(verdict))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check legacy build image selection with Docker"
    )
    parser.add_argument("output", type=Path)
    check(parser.parse_args().output.resolve())
