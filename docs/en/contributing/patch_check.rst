.. SPDX-License-Identifier: Apache-2.0

.. _contrib-patch-check:

Patch check
===========

This page covers the patch-check requirements, how to run the check locally, the
differences from the upstream script, and how to report false positives.

Scope and requirements
----------------------

Every non-merge commit submitted to this repository must pass
``scripts/host/checkpatch.pl`` without errors. The script is QEMU's
``scripts/host/checkpatch.pl``, and the repository follows the QEMU patch style it
enforces:

- Each commit carries a ``Signed-off-by:`` line in the exact form
  ``Signed-off-by: Name <email>``, taken from ``git config user.name`` and
  ``git config user.email``.
- Commit messages carry no AI attribution trailers, such as
  ``Co-authored-by:`` lines for AI tools, ``Assisted-by:``,
  ``Generated-by:``, or the ``🤖`` marker.
- Added lines contain no trailing whitespace, DOS line endings, or invalid
  UTF-8. Files end with a newline.
- Source files use spaces for indentation. Lines longer than 80 columns produce
  a warning and lines longer than 90 columns produce an error.
- Python scripts that declare an interpreter use ``python3``.
- C and C++ code follows the QEMU coding style: ``/* */`` comments, braces on
  all arms of ``if``/``else``, ``type *name`` pointer spacing, and
  function opening braces on their own line.
- New source files start with an ``SPDX-License-Identifier:`` line and do not
  copy license boilerplate text. ``Apache-2.0`` is the project license;
  ``MIT``, ``BSD-2-Clause`` and ``BSD-3-Clause`` are accepted for code
  derived from sources under those licenses, and the commit message explains
  the choice.

Errors fail the check. Warnings are reported and do not fail the check; review
each warning before submitting. The check covers the lines a commit adds or
modifies; existing code is checked when a commit changes it.

Running the check locally
-------------------------

Check every commit on the current branch that is not yet on ``origin/main``:

.. code-block:: bash

   git fetch origin
   just check-patch

Check commits since a specific revision:

.. code-block:: bash

   just check-patch <base-commit>

``just check-patch`` runs ``scripts/host/check_patch.sh``. The script prints only
the commits that have problems, prefixed with the commit hash and the patch line
number, and exits with a non-zero status when any commit has an error.
``just check`` also runs ``just check-patch`` together with ShellCheck and the
other host-side checks described in :doc:`workflow`.

Run ``scripts/host/checkpatch.pl`` directly for other inputs:

.. code-block:: bash

   # One commit or a revision range
   ./scripts/host/checkpatch.pl HEAD
   ./scripts/host/checkpatch.pl origin/main..HEAD

   # A patch file produced by git format-patch
   ./scripts/host/checkpatch.pl 0001-example.patch

   # Whole files instead of patches (does not check Signed-off-by)
   ./scripts/host/checkpatch.pl -f scripts/host/cosim_launch.sh

   # An uncommitted patch file
   just check-patch-file <patch>

``scripts/host/checkpatch.pl`` requires Perl 5 and must run inside the source tree.

Differences from QEMU's checkpatch.pl
-------------------------------------

``scripts/host/checkpatch.pl`` is copied from QEMU commit
``615ece3c406b262996e569f29ea6eed0d81c4d8d`` with these changes:

.. list-table::
   :header-rows: 1

   * - Area
     - Repository behavior
   * - Tree detection
     - Recognizes the repository root (``LICENSE``, ``README.md``,
       ``AGENTS.md``, ``.gitmodules``, ``docs``,
       ``scripts``, ``tests``)
   * - SPDX licenses
     - Prefers ``Apache-2.0``; also accepts ``MIT``,
       ``BSD-2-Clause``, ``BSD-3-Clause``
   * - SPDX requirement
     - New ``.cpp`` and ``.hpp`` files also require
       ``SPDX-License-Identifier``
   * - License boilerplate
     - Apache License header text is rejected in new files
   * - Messages
     - Error text refers to this repository instead of QEMU

All other checks are unchanged from QEMU. Checks for QEMU-only paths, such as
``linux-headers/``, ACPI test data and ``trace-events`` files, never match
this repository's paths.

The script keeps its upstream GPL-2.0 license. It is a development tool and is
not built into or distributed with the co-simulation binaries.

To update the script from QEMU, copy the new upstream
``scripts/host/checkpatch.pl``, apply the changes in the table above again, and
update the QEMU commit recorded in this section.

False positives
---------------

If ``scripts/host/checkpatch.pl`` reports an error on correct code, open an issue in
this repository with the commit and the full report. Fixing a false positive
follows the same update process as above.

Related pages
-------------

- :doc:`workflow`
- :doc:`ci`
- :doc:`maintainers`
