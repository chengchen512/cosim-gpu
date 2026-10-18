# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import shutil
import tempfile
import unittest

from resources.images.recipe import RecipeError, list_recipes, load_recipe


WORKSPACE = Path(__file__).resolve().parents[2]
RECIPE = "vhost/ubuntu/24.04/x86_64/rocm7_0"


class ImageRecipeTests(unittest.TestCase):
    def test_rocm_recipe_is_discoverable_and_has_a_pinned_base_image(self):
        self.assertIn(RECIPE, list_recipes(WORKSPACE))
        recipe = load_recipe(WORKSPACE, RECIPE)
        self.assertEqual(recipe.role, "vhost")
        self.assertEqual(recipe.distribution, "ubuntu")
        self.assertEqual(recipe.release, "24.04")
        self.assertEqual(recipe.architecture, "x86_64")
        self.assertEqual(len(recipe.base_sha256), 64)
        self.assertEqual(recipe.kernel_artifact, "kernel")

    def test_recipe_outputs_and_sources_stay_in_the_workspace(self):
        recipe = load_recipe(WORKSPACE, RECIPE)
        self.assertTrue(
            recipe.output_path(WORKSPACE).is_relative_to(WORKSPACE)
        )
        self.assertTrue(recipe.playbook_file.is_relative_to(WORKSPACE))
        self.assertTrue(recipe.tasks_file.is_relative_to(WORKSPACE))
        for path in recipe.inputs.values():
            self.assertTrue(path.is_relative_to(WORKSPACE))

    def test_recipe_image_inputs_are_present_at_declared_paths(self):
        recipe = load_recipe(WORKSPACE, RECIPE)
        external_firmware_inputs = {
            "mi200_rom": "mi200.rom",
            "mi300_rom": "mi300.rom",
            "mi300_discovery": "mi300_discovery",
            "mi350_discovery": "mi350_discovery",
        }
        self.assertLessEqual(
            external_firmware_inputs.keys(), recipe.inputs.keys()
        )
        for name, path in recipe.inputs.items():
            if name in recipe.reuse_optional_inputs:
                continue
            with self.subTest(input_name=name):
                if name in external_firmware_inputs:
                    expected = (
                        WORKSPACE
                        / "third_party/gem5-resources/src/x86-ubuntu-gpu-ml"
                        / "files"
                        / external_firmware_inputs[name]
                    )
                    self.assertEqual(path, expected)
                    submodule_metadata = (
                        WORKSPACE / "third_party/gem5-resources/.git"
                    )
                    if not path.is_file() and not submodule_metadata.exists():
                        # The fast CI job checks out no submodules.
                        continue
                else:
                    self.assertTrue(
                        path.resolve().is_relative_to(recipe.directory),
                        f"image input is outside its recipe: {path}",
                    )
                self.assertTrue(path.is_file(), f"missing image input: {path}")

    def test_recipe_identifier_rejects_parent_traversal(self):
        with self.assertRaises(RecipeError):
            load_recipe(WORKSPACE, "../../outside")

    def test_payload_disk_format_must_match_the_builder_output_format(self):
        recipe = load_recipe(WORKSPACE, RECIPE)
        with tempfile.TemporaryDirectory() as name:
            workspace = Path(name)
            recipe_directory = (
                workspace / "resources/images/recipes" / RECIPE
            )
            recipe_directory.parent.mkdir(parents=True)
            shutil.copytree(recipe.directory, recipe_directory)
            recipe_file = recipe_directory / "recipe.toml"
            content = recipe_file.read_text(encoding="utf-8")
            current = '[payload]\ndisk_id = "root"\ndisk_format = "qcow2"'
            mismatch = '[payload]\ndisk_id = "root"\ndisk_format = "raw"'
            self.assertIn(current, content)
            recipe_file.write_text(
                content.replace(current, mismatch, 1), encoding="utf-8"
            )

            with self.assertRaisesRegex(
                RecipeError,
                "payload.disk_format must match builder.disk_format",
            ):
                load_recipe(workspace, RECIPE)

    def test_bundle_metadata_names_cannot_be_provisioning_outputs(self):
        recipe = load_recipe(WORKSPACE, RECIPE)
        reserved_names = ("disk", "manifest.json", "packer.log", "build.log")
        for reserved_name in reserved_names:
            with self.subTest(output_name=reserved_name):
                with tempfile.TemporaryDirectory() as name:
                    workspace = Path(name)
                    recipe_directory = (
                        workspace / "resources/images/recipes" / RECIPE
                    )
                    recipe_directory.parent.mkdir(parents=True)
                    shutil.copytree(recipe.directory, recipe_directory)
                    recipe_file = recipe_directory / "recipe.toml"
                    content = recipe_file.read_text(encoding="utf-8")
                    content = content.replace(
                        'name = "kernel"',
                        f'name = "{reserved_name}"',
                        1,
                    )
                    recipe_file.write_text(content, encoding="utf-8")

                    with self.assertRaisesRegex(RecipeError, "is reserved"):
                        load_recipe(workspace, RECIPE)


if __name__ == "__main__":
    unittest.main()
