# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import tomllib
from typing import TypedDict

RESERVED_OUTPUT_NAMES = {"disk", "manifest.json", "packer.log", "build.log"}


class BaseData(TypedDict):
    url: str
    sha256: str
    format: str


class BuilderData(TypedDict):
    image_name: str
    disk_size: str
    disk_format: str
    cpus: int
    memory_mb: int
    ssh_username: str
    accelerator: str
    machine_type: str
    cpu_model: str


class OutputData(TypedDict):
    name: str
    guest_path: str


class ProvisioningData(TypedDict):
    playbook: str
    tasks: str
    variables: dict[str, str]
    outputs: list[OutputData]


class PayloadData(TypedDict):
    disk_id: str
    disk_format: str
    disk_bus: str
    kernel_artifact: str | None
    kernel_cmdline: str | None


class RecipeData(TypedDict):
    schema: int
    id: str
    role: str
    distribution: str
    release: str
    architecture: str
    base: BaseData
    builder: BuilderData
    provisioning: ProvisioningData
    payload: PayloadData
    inputs: dict[str, str]
    reuse_optional_inputs: list[str]


class RecipeError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactOutput:
    name: str
    guest_path: str


@dataclass(frozen=True)
class ImageRecipe:
    identifier: str
    directory: Path
    recipe_file: Path
    role: str
    distribution: str
    release: str
    architecture: str
    base_url: str
    base_sha256: str
    base_format: str
    image_name: str
    disk_size: str
    disk_format: str
    cpus: int
    memory_mb: int
    ssh_username: str
    accelerator: str
    machine_type: str
    cpu_model: str
    playbook_file: Path
    tasks_file: Path
    variables: dict[str, str]
    outputs: tuple[ArtifactOutput, ...]
    disk_id: str
    disk_bus: str
    kernel_artifact: str | None
    kernel_cmdline: str | None
    inputs: dict[str, Path]
    reuse_optional_inputs: tuple[str, ...]

    def output_path(self, workspace: Path) -> Path:
        return workspace / "build" / "images" / self.identifier


def list_recipes(workspace: Path) -> list[str]:
    recipes = workspace / "resources/images/recipes"
    if not recipes.is_dir():
        return []
    return sorted(
        path.relative_to(recipes).parent.as_posix()
        for path in recipes.rglob("recipe.toml")
        if path.is_file()
    )


def load_recipe(workspace: Path, identifier: str) -> ImageRecipe:
    safe_identifier = _relative_path(identifier, "recipe id")
    recipe_file = workspace / "resources/images/recipes" / safe_identifier
    recipe_file = recipe_file / "recipe.toml"
    if not recipe_file.is_file():
        raise RecipeError(f"image recipe not found: {identifier}")
    try:
        data = tomllib.loads(recipe_file.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RecipeError(
            f"cannot read image recipe {recipe_file}: {error}"
        ) from error
    if not isinstance(data, dict):
        raise RecipeError(
            f"image recipe must be a TOML table: {recipe_file}"
        )
    _require(data, "schema", int)
    if data["schema"] != 1:
        raise RecipeError(f"unsupported recipe schema {data['schema']}")
    _require(data, "id", str)
    if data["id"] != identifier:
        raise RecipeError(
            f"recipe id {data['id']!r} does not match {identifier!r}"
        )
    for key in ("role", "distribution", "release", "architecture"):
        _require(data, key, str)
    if data["role"] != "vhost":
        raise RecipeError("recipe.role must be vhost")
    if data["architecture"] not in {"x86_64", "aarch64", "riscv64"}:
        raise RecipeError(
            f"unsupported recipe architecture {data['architecture']!r}"
        )
    base = _mapping(data, "base")
    _require(base, "url", str)
    _require(base, "sha256", str)
    _require(base, "format", str)
    if not base["url"].startswith("https://"):
        raise RecipeError("base.url must use HTTPS")
    if not re.fullmatch(r"[0-9a-f]{64}", base["sha256"]):
        raise RecipeError("base.sha256 must be a lowercase SHA-256 digest")
    if base["format"] not in {"raw", "qcow2"}:
        raise RecipeError("base.format must be raw or qcow2")

    builder = _mapping(data, "builder")
    for key in (
        "image_name", "disk_size", "disk_format", "ssh_username", "accelerator",
        "machine_type", "cpu_model",
    ):
        _require(builder, key, str)
    for key in ("cpus", "memory_mb"):
        _require(builder, key, int)
    if builder["disk_format"] not in {"raw", "qcow2"}:
        raise RecipeError("builder.disk_format must be raw or qcow2")
    if builder["cpus"] < 1 or builder["memory_mb"] < 512:
        raise RecipeError("builder CPU and memory values are out of range")
    if builder["accelerator"] not in {"kvm", "tcg", "hvf"}:
        raise RecipeError("builder.accelerator must be kvm, tcg or hvf")

    provisioning = _mapping(data, "provisioning")
    _require(provisioning, "playbook", str)
    _require(provisioning, "tasks", str)
    variables = _mapping(provisioning, "variables")
    outputs_data = provisioning.get("outputs")
    if not isinstance(outputs_data, list) or not outputs_data:
        raise RecipeError(
            "provisioning.outputs must contain at least one artifact"
        )
    outputs: list[ArtifactOutput] = []
    for index, item in enumerate(outputs_data):
        if not isinstance(item, dict):
            raise RecipeError(
                f"provisioning.outputs[{index}] must be an object"
            )
        _require(item, "name", str)
        _require(item, "guest_path", str)
        name = item["name"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise RecipeError(f"invalid artifact name {name!r}")
        if name in RESERVED_OUTPUT_NAMES:
            raise RecipeError(
                f"provisioning.outputs[{index}].name is reserved: {name}"
            )
        guest_path = Path(item["guest_path"])
        if not guest_path.is_absolute() or ".." in guest_path.parts:
            raise RecipeError(
                f"artifact guest_path must be absolute: {guest_path}"
            )
        outputs.append(ArtifactOutput(name, item["guest_path"]))
    if len({output.name for output in outputs}) != len(outputs):
        raise RecipeError("provisioning.outputs names must be unique")

    recipe_directory = recipe_file.parent.resolve()
    playbook_file = _inside_directory(
        recipe_directory,
        provisioning["playbook"],
        "provisioning.playbook",
    )
    tasks_file = _inside_directory(
        recipe_directory,
        provisioning["tasks"],
        "provisioning.tasks",
    )
    if not playbook_file.is_file():
        raise RecipeError(
            f"recipe Ansible playbook not found: {playbook_file}"
        )
    if not tasks_file.is_file():
        raise RecipeError(f"recipe tasks file not found: {tasks_file}")

    payload = _mapping(data, "payload")
    for key in ("disk_id", "disk_format", "disk_bus"):
        _require(payload, key, str)
    kernel_artifact = payload.get("kernel_artifact")
    kernel_cmdline = payload.get("kernel_cmdline")
    if kernel_artifact is not None and not isinstance(kernel_artifact, str):
        raise RecipeError("payload.kernel_artifact must be a string or null")
    if kernel_cmdline is not None and not isinstance(kernel_cmdline, str):
        raise RecipeError("payload.kernel_cmdline must be a string or null")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", payload["disk_id"]):
        raise RecipeError(f"invalid payload disk id {payload['disk_id']!r}")
    if payload["disk_format"] not in {"raw", "qcow2"}:
        raise RecipeError("payload.disk_format must be raw or qcow2")
    if payload["disk_format"] != builder["disk_format"]:
        raise RecipeError(
            "payload.disk_format must match builder.disk_format"
        )
    if payload["disk_bus"] not in {"virtio", "nvme", "ide", "scsi"}:
        raise RecipeError("payload.disk_bus is unsupported")
    if (
        kernel_artifact is not None
        and kernel_artifact not in {output.name for output in outputs}
    ):
        raise RecipeError(
            "payload.kernel_artifact must name a declared output"
        )
    if kernel_artifact is None and kernel_cmdline is not None:
        raise RecipeError(
            "payload.kernel_cmdline requires payload.kernel_artifact"
        )

    inputs_data = _mapping(data, "inputs")
    if not inputs_data:
        raise RecipeError("inputs must list Host files used by the recipe")
    inputs = {
        name: workspace / _relative_path(path, f"inputs.{name}")
        for name, path in inputs_data.items()
        if isinstance(name, str) and isinstance(path, str)
    }
    if len(inputs) != len(inputs_data):
        raise RecipeError("inputs must map names to workspace-relative paths")
    optional_inputs = data.get("reuse_optional_inputs", [])
    if not isinstance(optional_inputs, list) or not all(
        isinstance(name, str) for name in optional_inputs
    ):
        raise RecipeError(
            "reuse_optional_inputs must be an array of input names"
        )
    if not set(optional_inputs).issubset(inputs):
        raise RecipeError("reuse_optional_inputs must name declared inputs")

    return ImageRecipe(
        identifier=identifier,
        directory=recipe_directory,
        recipe_file=recipe_file.resolve(),
        role=data["role"],
        distribution=data["distribution"],
        release=data["release"],
        architecture=data["architecture"],
        base_url=base["url"],
        base_sha256=base["sha256"],
        base_format=base["format"],
        image_name=builder["image_name"],
        disk_size=builder["disk_size"],
        disk_format=builder["disk_format"],
        cpus=builder["cpus"],
        memory_mb=builder["memory_mb"],
        ssh_username=builder["ssh_username"],
        accelerator=builder["accelerator"],
        machine_type=builder["machine_type"],
        cpu_model=builder["cpu_model"],
        playbook_file=playbook_file,
        tasks_file=tasks_file,
        variables=dict(variables),
        outputs=tuple(outputs),
        disk_id=payload["disk_id"],
        disk_bus=payload["disk_bus"],
        kernel_artifact=kernel_artifact,
        kernel_cmdline=kernel_cmdline,
        inputs=inputs,
        reuse_optional_inputs=tuple(optional_inputs),
    )


def _require(data: dict, key: str, expected: type) -> None:
    if key not in data or not isinstance(data[key], expected):
        raise RecipeError(f"recipe field {key!r} must be {expected.__name__}")


def _mapping(data: dict, key: str) -> dict:
    value = data.get(key)
    if not isinstance(value, dict):
        raise RecipeError(f"recipe field {key!r} must be an object")
    return value


def _relative_path(value: str, what: str) -> Path:
    path = PurePosixPath(value)
    if (
        "\\" in value
        or path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise RecipeError(f"{what} must be a safe relative path: {value!r}")
    return Path(*path.parts)


def _inside_directory(root: Path, value: str, what: str) -> Path:
    relative = _relative_path(value, what)
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise RecipeError(f"{what} escapes its recipe directory")
    return candidate
