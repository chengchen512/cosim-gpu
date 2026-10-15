# SPDX-License-Identifier: Apache-2.0

import argparse
from dataclasses import asdict, dataclass
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import zipfile

from ci_lifecycle import Lifecycle
from rocm_assets import input_key, signal_group, verify


@dataclass(frozen=True)
class Scope:
    repository: str
    head_repository: int
    branch: str

    @classmethod
    def environment(cls) -> "Scope":
        return cls(
            os.environ["GITHUB_REPOSITORY"],
            int(os.environ["COSIM_ARTIFACT_HEAD_REPO"]),
            os.environ["COSIM_ARTIFACT_BRANCH"],
        )

    def includes(self, artifact: dict) -> bool:
        run = artifact.get("workflow_run")
        return bool(
            run and not artifact["expired"]
            and run["head_repository_id"] == self.head_repository
            and run["head_branch"] == self.branch
        )


@dataclass(frozen=True)
class PublishedImage:
    artifact_id: int
    run_id: int
    manifest: dict


class ArtifactMissing(RuntimeError):
    pass


def github(arguments: list[str], lifecycle: Lifecycle) -> bytes:
    lifecycle.check()
    with subprocess.Popen(
        ["gh", "api", *arguments], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, start_new_session=True,
    ) as process:
        with lifecycle.own(process):
            try:
                output, errors = process.communicate(timeout=60)
                lifecycle.check()
                if process.returncode:
                    try:
                        response = json.loads(output)
                    except (ValueError, UnicodeError):
                        response = {}
                    if (isinstance(response, dict)
                            and str(response.get("status")) in ("404", "410")):
                        raise ArtifactMissing(errors.decode(errors="replace"))
                    raise RuntimeError(errors.decode(errors="replace"))
                return output
            finally:
                if process.poll() is None or lifecycle.reason is not None:
                    signal_group(process, signal.SIGKILL)
                    process.wait()


def require_key(manifest: dict, key: str) -> None:
    if (manifest["schema"] != 1 or manifest["input_key"] != key
            or input_key(manifest["inputs"]) != key):
        raise ValueError("ROCm artifact does not match the requested inputs")


def find_image(
    key: str, scope: Scope, lifecycle: Lifecycle,
) -> PublishedImage | None:
    endpoint = f"repos/{scope.repository}/actions/artifacts"
    pages = json.loads(github(
        [f"{endpoint}?per_page=100", "--paginate", "--slurp"], lifecycle
    ))
    artifacts = [
        artifact for page in pages for artifact in page["artifacts"]
        if scope.includes(artifact)
    ]
    records = {
        (artifact["workflow_run"]["id"], artifact["name"]): artifact
        for artifact in artifacts
    }
    prefix = "rocm-guest-"
    for artifact in artifacts:
        if not artifact["name"].startswith(prefix):
            continue
        run_id = artifact["workflow_run"]["id"]
        suffix = artifact["name"][len(prefix):]
        metadata = records.get((run_id, "rocm-image-logs-" + suffix))
        if metadata is None or metadata["size_in_bytes"] > 32 * 1024**2:
            continue
        try:
            content = github([f"{endpoint}/{metadata['id']}/zip"], lifecycle)
        except ArtifactMissing:
            continue
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            try:
                member = archive.getinfo("rocm-assets/manifest.json")
            except KeyError:
                continue
            if member.file_size > 64 * 1024:
                raise ValueError("ROCm artifact manifest exceeds 64 KiB")
            manifest = json.loads(archive.read(member))
        if manifest.get("input_key") != key:
            continue
        require_key(manifest, key)
        lifecycle.check()
        return PublishedImage(artifact["id"], run_id, manifest)
    lifecycle.check()
    return None


def verify_image(output: Path, key: str) -> None:
    manifest = json.loads((output / "manifest.json").read_text())
    require_key(manifest, key)
    verify(output)


def record_selection(image: PublishedImage | None, record: Path) -> Path | None:
    parent = record.resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    directory = None
    value = None
    if image is not None:
        directory = Path(tempfile.mkdtemp(prefix="rocm-retained-", dir=parent))
        value = {**asdict(image), "download_directory": str(directory)}
    record.write_text(json.dumps(value, indent=2) + "\n")
    return directory


def discard_download(record: Path) -> None:
    value = json.loads(record.read_text())
    directory = Path(value["download_directory"])
    if (directory.parent.resolve() != record.resolve().parent
            or not directory.name.startswith("rocm-retained-")):
        raise ValueError("download cleanup must stay in its staging directory")
    if directory.is_symlink() or directory.is_file():
        directory.unlink()
    elif directory.exists():
        shutil.rmtree(directory)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reuse scoped ROCm artifacts by verified input identity"
    )
    commands = parser.add_subparsers(dest="operation", required=True)
    finder = commands.add_parser("find")
    finder.add_argument("input_key")
    finder.add_argument("record", type=Path)
    verifier = commands.add_parser("verify")
    verifier.add_argument("output", type=Path)
    verifier.add_argument("input_key")
    adopter = commands.add_parser("adopt")
    adopter.add_argument("source", type=Path)
    adopter.add_argument("output", type=Path)
    adopter.add_argument("input_key")
    discard = commands.add_parser("discard")
    discard.add_argument("record", type=Path)
    args = parser.parse_args()
    with Lifecycle().installed() as lifecycle:
        if args.operation == "discard":
            discard_download(args.record)
        elif args.operation == "adopt":
            verify_image(args.source, args.input_key)
            lifecycle.check()
            if args.output.exists() or args.output.is_symlink():
                raise FileExistsError(args.output)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.source.rename(args.output)
        elif args.operation == "verify":
            verify_image(args.output, args.input_key)
        else:
            image = find_image(args.input_key, Scope.environment(), lifecycle)
            directory = record_selection(image, args.record)
            print(f"artifact-id={image.artifact_id if image else ''}")
            print(f"run-id={image.run_id if image else ''}")
            print(f"download-dir={directory if directory else ''}")
        lifecycle.check()


if __name__ == "__main__":
    main()
