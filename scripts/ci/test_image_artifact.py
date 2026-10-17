# SPDX-License-Identifier: Apache-2.0

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from image_artifact import image_bundle_root, image_manifest_member


class ImageManifestMemberTests(unittest.TestCase):
    def archive_with(self, path: str) -> zipfile.ZipFile:
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w") as archive:
            archive.writestr(path, "{}")
        return zipfile.ZipFile(io.BytesIO(content.getvalue()))

    def test_finds_manifest_in_build_rooted_diagnostic_artifact(self):
        with self.archive_with("build/rocm-assets/manifest.json") as archive:
            member = image_manifest_member(archive)
        self.assertIsNotNone(member)
        self.assertEqual(member.filename, "build/rocm-assets/manifest.json")

    def test_finds_manifest_in_existing_diagnostic_artifact(self):
        with self.archive_with("rocm-assets/manifest.json") as archive:
            member = image_manifest_member(archive)
        self.assertIsNotNone(member)
        self.assertEqual(member.filename, "rocm-assets/manifest.json")

    def test_missing_manifest_is_ignored(self):
        with self.archive_with("build/rocm-assets/build.log") as archive:
            self.assertIsNone(image_manifest_member(archive))


class ImageBundleRootTests(unittest.TestCase):
    def test_uses_manifest_at_download_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            download = Path(temporary)
            (download / "manifest.json").write_text("{}\n")

            self.assertEqual(image_bundle_root(download), download)

    def test_finds_manifest_in_nested_download_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            download = Path(temporary)
            bundle = download / "rocm-guest-38995128420-1"
            bundle.mkdir()
            (bundle / "manifest.json").write_text("{}\n")

            self.assertEqual(image_bundle_root(download), bundle)

    def test_rejects_ambiguous_nested_manifests(self):
        with tempfile.TemporaryDirectory() as temporary:
            download = Path(temporary)
            first = download / "first"
            second = download / "second"
            first.mkdir()
            second.mkdir()
            (first / "manifest.json").write_text("{}\n")
            (second / "manifest.json").write_text("{}\n")

            with self.assertRaisesRegex(
                ValueError, "expected one ROCm artifact manifest"
            ):
                image_bundle_root(download)
