# SPDX-License-Identifier: Apache-2.0

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import shutil
import signal
import subprocess
import time
import uuid

from ci_lifecycle import Lifecycle
from runtime_artifact import ROOT, sha256


RESOURCE = ROOT / "gem5-resources"
RECIPE = Path("src/x86-ubuntu-gpu-ml")
SOURCE = RESOURCE / RECIPE
PRODUCTS = (
    "kernel", "disk", "image-packages.tsv", "kernel-release",
    "python-packages.json", "amdgpu-module.txt", "hipcc-version.txt",
    "os-release",
)


def tracked_recipe() -> list[Path]:
    names = subprocess.check_output([
        "git", "-C", str(RESOURCE), "ls-files", "-z", "--", str(RECIPE),
    ]).split(b"\0")
    return [Path(os.fsdecode(name)) for name in names if name]


def inputs(disk_format: str) -> dict:
    image_name = os.environ.get("PKR_VAR_image_name", "x86-ubuntu-rocm70")
    if (not image_name or image_name in (".", "..")
            or Path(image_name).name != image_name):
        raise ValueError("Packer image_name must name a single file")
    digest = hashlib.sha256()
    for relative in sorted(tracked_recipe()):
        path = RESOURCE / relative
        digest.update(os.fsencode(relative) + b"\0")
        digest.update(str(path.stat().st_mode).encode() + b"\0")
        digest.update(path.read_bytes())
    revisions = {}
    for name in ("gem5", "gem5-resources"):
        revisions[name] = subprocess.check_output([
            "git", "-C", str(ROOT / name), "rev-parse", "HEAD",
        ], text=True).strip()
    return {
        "schema": 1, "architecture": "x86_64", "format": disk_format,
        "image_name": image_name,
        "recipe_sha256": digest.hexdigest(), "sources": revisions,
        "m5_sha256": sha256(SOURCE / "files/m5"),
        "builder_sha256": sha256(Path(__file__)),
        "qemu_version": subprocess.check_output(
            [str(qemu_binary()), "--version"], text=True
        ).splitlines()[0],
        "qemu_sha256": sha256(qemu_binary()),
        "packer_variables_sha256": input_key({
            name: value for name, value in os.environ.items()
            if name.startswith("PKR_VAR_")
        }),
        "epoch": os.environ.get("COSIM_ROCM_IMAGE_EPOCH", "1"),
    }


def input_key(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def qemu_binary() -> Path:
    requested = os.environ.get("QEMU_BIN")
    local = ROOT / "qemu/build/qemu-system-x86_64"
    if requested:
        selected = shutil.which(requested)
    elif local.is_file() and os.access(local, os.X_OK):
        selected = str(local)
    else:
        selected = shutil.which("qemu-system-x86_64")
    if selected is None:
        raise RuntimeError("build QEMU with just build-qemu or set QEMU_BIN")
    return Path(selected).resolve()


def verify(output: Path, expected: dict | None = None) -> dict:
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest["schema"] != 1 or manifest["input_key"] != input_key(
        manifest["inputs"]
    ):
        raise ValueError("invalid ROCm image provenance")
    if expected is not None and manifest["inputs"] != expected:
        raise ValueError("ROCm image inputs differ from the requested build")
    for name in PRODUCTS:
        if sha256(output / name) != manifest[name]["sha256"]:
            raise ValueError(f"ROCm image checksum mismatch: {name}")
    subprocess.run(["readelf", "--file-header", str(output / "kernel")],
                   check=True, stdout=subprocess.DEVNULL)
    info = json.loads(subprocess.check_output([
        "qemu-img", "info", "--output=json", "-f", manifest["disk"]["format"],
        str(output / "disk"),
    ]))
    if info.get("backing-filename") or info.get("encrypted"):
        raise ValueError("ROCm base image must be standalone and unencrypted")
    if manifest["disk"]["format"] == "qcow2":
        subprocess.run(["qemu-img", "check", "-q", "-f", "qcow2",
                        str(output / "disk")], check=True)
    with (output / "image-packages.tsv").open() as stream:
        packages = dict(csv.reader(stream, delimiter="\t"))
    for package in ("rocm", "amdgpu-dkms", "hipcc"):
        if not packages.get(package):
            raise ValueError(f"ROCm image is missing {package}")
    return manifest


def stage_recipe(stage: Path) -> None:
    stage.mkdir(parents=True)
    for relative in tracked_recipe():
        destination = stage / relative.relative_to(RECIPE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RESOURCE / relative, destination)
    m5 = SOURCE / "files/m5"
    if m5.is_file():
        shutil.copy2(m5, stage / "files/m5")


def run_logged(command: list[str], stage: Path, lifecycle: Lifecycle) -> None:
    environment = {**os.environ, "PACKER_LOG": "1",
                   "PACKER_LOG_PATH": str(stage / "packer.log")}
    with (stage / "build.log").open("wb") as log:
        process = subprocess.Popen(command, cwd=stage, env=environment,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   start_new_session=True)
        with lifecycle.own(process):
            try:
                assert process.stdout is not None
                deadline = None
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while selector.get_map():
                        if lifecycle.reason is not None and deadline is None:
                            signal_group(process, signal.SIGTERM)
                            deadline = time.monotonic() + 10
                        expired = (
                            deadline is not None
                            and time.monotonic() >= deadline
                        )
                        if expired:
                            signal_group(process, signal.SIGKILL)
                            raise RuntimeError("image cleanup timed out")
                        for key, _ in selector.select(timeout=0.2):
                            chunk = os.read(key.fd, 65536)
                            if not chunk:
                                selector.unregister(key.fileobj)
                                continue
                            log.write(chunk)
                            log.flush()
                            print(chunk.decode(errors="replace"),
                                  end="", flush=True)
                status = process.wait()
                lifecycle.check()
                if status != 0:
                    raise RuntimeError(f"Packer failed ({status}); see {stage}")
            finally:
                if lifecycle.reason is not None or process.poll() is None:
                    signal_group(process, signal.SIGTERM)
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        signal_group(process, signal.SIGKILL)
                        process.wait()
                if process.stdout is not None:
                    process.stdout.close()


def signal_group(process: subprocess.Popen, number: int) -> None:
    try:
        os.killpg(process.pid, number)
    except ProcessLookupError:
        pass


def build(output: Path, disk_format: str, lifecycle: Lifecycle) -> None:
    requested = inputs(disk_format)
    if output.exists():
        verify(output, requested)
        lifecycle.check()
        print(f"Reusing verified ROCm image: {output}")
        return
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("ROCm image construction requires Linux x86_64/KVM")
    with Path("/dev/kvm").open("rb+"):
        pass
    for name in (
        "qemu-img", "curl", "unzip", "shasum", "readelf"
    ):
        if shutil.which(name) is None:
            raise RuntimeError(f"missing image build dependency: {name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output.parent).free < 60 * 1024**3:
        raise RuntimeError("ROCm image construction requires 60 GiB free space")
    stage = output.parent / ("rocm-image-build-" + uuid.uuid4().hex[:8])
    stage_recipe(stage)
    qemu = qemu_binary()
    command = ["bash", "build.sh", "-color=false",
               "-var", f"qemu_path={qemu}",
               "-var", f"image_name={requested['image_name']}",
               "-var", f"disk_format={disk_format}"]
    proxy = os.environ.get("https_proxy", "")
    if proxy:
        command += ["-var", f"http_proxy={proxy}"]
    run_logged(command, stage, lifecycle)
    lifecycle.check()
    products = stage / "products"
    products.mkdir()
    (stage / "vmlinux-rocm70").rename(products / "kernel")
    (stage / "disk-image" / requested["image_name"]).rename(products / "disk")
    for name in PRODUCTS[2:]:
        (stage / name).rename(products / name)
    manifest = {
        "schema": 1, "input_key": input_key(requested), "inputs": requested,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "build_run": os.environ.get("GITHUB_RUN_ID", "local"),
        "build_revision": os.environ.get("GITHUB_SHA", "local"),
        "kernel_release": (products / "kernel-release").read_text().strip(),
        **{name: {"sha256": sha256(products / name)} for name in PRODUCTS},
    }
    manifest["disk"]["format"] = disk_format
    (products / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    verify(products, requested)
    lifecycle.check()
    for name in ("build.log", "packer.log"):
        shutil.copy2(stage / name, products / name)
    products.rename(output)
    # Only this invocation's generated staging directory is removed.
    shutil.rmtree(stage)
    lifecycle.check()
    print(f"Built and verified ROCm image: {output}")


def install_local(output: Path) -> None:
    manifest = verify(output, inputs("raw"))
    record = SOURCE / "disk-image/cosim-image.json"
    destinations = {
        "kernel": SOURCE / "vmlinux-rocm70",
        "disk": SOURCE / "disk-image/x86-ubuntu-rocm70",
    }
    if record.is_file():
        previous = json.loads(record.read_text())
        kernel_matches = (
            sha256(destinations["kernel"]) == manifest["kernel"]["sha256"]
            if destinations["kernel"].is_file() else False
        )
        if (previous["input_key"] == manifest["input_key"]
                and all(path.is_file() for path in destinations.values())
                and kernel_matches):
            print("Reusing the installed local image and its writable disk")
            return
    for destination in destinations.values():
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"preserve existing local image: {destination}")
    install_copies({output / name: path for name, path in destinations.items()})
    record.write_text(json.dumps({"input_key": manifest["input_key"]}) + "\n")


def install_copies(files: dict[Path, Path]) -> None:
    pending = {}
    published = []
    try:
        for source, destination in files.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(
                destination.name + ".cosim-copy-" + uuid.uuid4().hex
            )
            pending[temporary] = destination
            subprocess.run(["cp", "--reflink=auto", "--sparse=always",
                            str(source), str(temporary)], check=True)
        for temporary, destination in pending.items():
            os.link(temporary, destination)
            published.append(destination)
    except BaseException:
        for destination in published:
            destination.unlink()
        raise
    finally:
        for temporary in pending:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and verify ROCm images")
    parser.add_argument("operation", choices=(
        "key", "build", "verify", "validate", "syntax", "install-local",
    ))
    parser.add_argument("--output", type=Path,
                        default=Path("artifacts/rocm-assets"))
    parser.add_argument("--format", choices=("raw", "qcow2"), default="qcow2")
    args = parser.parse_args()
    output = args.output.resolve()
    with Lifecycle().installed() as lifecycle:
        if args.operation == "key":
            print(input_key(inputs(args.format)))
        elif args.operation == "build":
            build(output, args.format, lifecycle)
        elif args.operation == "verify":
            verify(output)
        elif args.operation == "install-local":
            install_local(output)
        else:
            stage_recipe(output)
            command = ["bash", "build.sh", "--validate"]
            if args.operation == "syntax":
                command.append("-syntax-only")
            else:
                command += ["-var", f"qemu_path={qemu_binary()}"]
            run_logged(command, output, lifecycle)
        lifecycle.check()


if __name__ == "__main__":
    main()
