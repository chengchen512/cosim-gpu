[中文](../zh/contributing.md)

# Contributing

This page defines the patch requirements for the top-level cosim-gpu
repository. Changes inside the `gem5` and `gem5-resources` submodules follow
the rules of those repositories.

## Patch Check Requirement

Every non-merge commit submitted to cosim-gpu must pass
`scripts/checkpatch.pl` without errors. The script is QEMU's
`scripts/checkpatch.pl`, and cosim-gpu follows the QEMU patch style it
enforces:

- Each commit carries a `Signed-off-by:` line in the exact form
  `Signed-off-by: Name <email>`, taken from `git config user.name` and
  `git config user.email`.
- Commit messages carry no AI attribution trailers, such as
  `Co-authored-by:` lines for AI tools, `Assisted-by:`, `Generated-by:`, or
  the `🤖` marker.
- Added lines contain no trailing whitespace, DOS line endings, or invalid
  UTF-8. Files end with a newline.
- Source files (`.c`, `.h`, `.cpp`, `.py`, `.sh`, `.pl`, and similar) use
  spaces for indentation. Lines longer than 80 columns produce a warning and
  lines longer than 90 columns produce an error.
- Python scripts that declare an interpreter use `python3`.
- C and C++ code (`.c`, `.h`, `.cpp`) follows the QEMU coding style: `/* */`
  comments, braces on all arms of `if`/`else`, `type *name` pointer
  spacing, and function opening braces on their own line.
- New source files start with an `SPDX-License-Identifier:` line and do not
  copy license boilerplate text. `Apache-2.0` is the project license;
  `MIT`, `BSD-2-Clause`, and `BSD-3-Clause` are accepted for code derived
  from sources under those licenses, and the commit message explains the
  choice.

Errors fail the check. Warnings are reported and do not fail the check;
review each warning before submitting.

The check covers the lines a commit adds or modifies. Existing code is checked
when a commit changes it.

## Running the Check Locally

Check every commit on the current branch that is not yet on `origin/main`:

```bash
git fetch origin
just checkpatch
```

Check commits since a specific revision:

```bash
just checkpatch <base-commit>
```

`just checkpatch` runs `scripts/check_patch.sh`, which prints only the commits
that have problems, prefixed with the commit hash and the patch line number,
and exits with a non-zero status when any commit has an error.

`just check` runs `just checkpatch` together with ShellCheck.

Run `scripts/checkpatch.pl` directly for other inputs:

```bash
# One commit or a revision range
./scripts/checkpatch.pl HEAD
./scripts/checkpatch.pl origin/main..HEAD

# A patch file produced by git format-patch
./scripts/checkpatch.pl 0001-example.patch

# Whole files instead of patches (does not check Signed-off-by)
./scripts/checkpatch.pl -f scripts/cosim_launch.sh
```

`scripts/checkpatch.pl` requires Perl 5 and must run inside the cosim-gpu
tree.

## Continuous Integration

The `Checkpatch` job in `.github/workflows/ci.yml` runs `just checkpatch` on
every pull request to `main` and every push to `main`:

| Event | Checked commits |
|-------|-----------------|
| Pull request | `<PR base commit>..<PR head commit>` |
| Push to `main` | `<previous main tip>..<new main tip>` |
| Push without a previous tip | The pushed tip commit |

A failing job blocks the pull request. Fix the reported lines, amend or
rebase the commits, and force-push the branch.

## Differences from QEMU's checkpatch.pl

`scripts/checkpatch.pl` is copied from QEMU commit
`615ece3c406b262996e569f29ea6eed0d81c4d8d` with these cosim-gpu changes:

| Area | cosim-gpu behavior |
|------|--------------------|
| Tree detection | Recognizes the cosim-gpu root (`LICENSE`, `README.md`, `agents.md`, `.gitmodules`, `docs`, `scripts`, `tests`) |
| SPDX licenses | Prefers `Apache-2.0`; also accepts `MIT`, `BSD-2-Clause`, `BSD-3-Clause` |
| SPDX requirement | New `.cpp` and `.hpp` files also require `SPDX-License-Identifier` |
| License boilerplate | Apache License header text is rejected in new files |
| Messages | Error text refers to cosim-gpu instead of QEMU |

All other checks are unchanged from QEMU. Checks for QEMU-only paths, such as
`linux-headers/`, ACPI test data, and `trace-events` files, never match
cosim-gpu paths.

The script keeps its upstream GPL-2.0 license. It is a development tool and is
not built into or distributed with the co-simulation binaries.

To update the script from QEMU, copy the new upstream
`scripts/checkpatch.pl`, apply the changes in the table above again, and
update the QEMU commit recorded in this section.

## False Positives

If `scripts/checkpatch.pl` reports an error on correct code, open an issue in
the cosim-gpu repository with the commit and the full report.
