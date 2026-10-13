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

`just check` runs `just checkpatch` together with ShellCheck and the
`MAINTAINERS.yml` check described below.

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

## Maintainers and Review Assignment

`MAINTAINERS.yml` divides the repository into areas, such as the QEMU frontend,
each accelerator backend, the guest image, and the build system. Each area
lists its files and the GitHub IDs of its maintainers and collaborators. The
file format follows Zephyr's `MAINTAINERS.yml` and is documented in the comment
at the top of the file.

### Looking Up Maintainers

`scripts/get_maintainer.py` (from Zephyr) reads `MAINTAINERS.yml`. Install its
Python dependencies once:

```bash
pip install -r scripts/ci/requirements.txt
```

Then query it through just:

```bash
just maintainers scripts/cosim_launch.sh tests/   # areas for paths
just maintainers-commits origin/main..            # areas touched by commits
just maintainers-areas                            # all areas and maintainers
```

`python3 scripts/get_maintainer.py --help` lists the other subcommands, such as
`orphaned` and `count`.

### Checks

| Check | Where | Fails when |
|-------|-------|------------|
| `just maintainers-check` | `Maintainers` job in `ci.yml` | `MAINTAINERS.yml` has an unknown key, a bad status, a malformed list, a glob that matches no file, a directory glob without a trailing `/`, an invalid regex, or a maintained area without maintainers; or a tracked file belongs to no area |
| `scripts/ci/check_maintainer_changes.py` | `assigner.yml` | A pull request adds a maintainer or collaborator who lacks at least triage access to the repository |

Every tracked file must belong to an area. When a commit adds a file outside the
existing areas, update `MAINTAINERS.yml` in the same commit.

### Automatic Assignment

`.github/workflows/assigner.yml` runs `scripts/ci/set_assignees.py` (from
Zephyr) when a pull request to `main` is opened, updated, reopened, or marked
ready for review:

- The labels of every affected area are added to the pull request.
- The maintainers and collaborators of every affected area are requested as
  reviewers, except the pull request author and people who removed themselves
  from the review request.
- The maintainers of the area with the most changed files are assigned. If the
  author is the only maintainer of that area, the next area is used.
  `Documentation` maintainers are assigned only when no other area is affected.
- When `MAINTAINERS.yml` changes, the maintainers of every changed area are
  also requested as reviewers.

When an issue is labeled, the maintainers of the area that owns those labels
are assigned to it.

The workflow uses `pull_request_target` and runs the scripts from the `main`
branch. It reads only `MAINTAINERS.yml` from the pull request, and only as
data, so pull requests from forks cannot change what the workflow executes.

### Adding a Maintainer

1. Give the person at least triage access to the GitHub repository.
2. Add their GitHub ID under `maintainers` or `collaborators` of the area in
   `MAINTAINERS.yml`.
3. Open a pull request. The current maintainers of that area are requested as
   reviewers, and the access check fails if step 1 was skipped.

## False Positives

If `scripts/checkpatch.pl` reports an error on correct code, open an issue in
the cosim-gpu repository with the commit and the full report.
