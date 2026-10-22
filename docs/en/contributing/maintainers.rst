.. SPDX-License-Identifier: Apache-2.0

.. _contrib-maintainers:

Maintainers
===========

``MAINTAINERS.yml`` divides the repository into areas and records each area's
maintainers, collaborators and labels. This page covers area ownership, the
related checks, automatic assignment and adding maintainers.

Areas and file ownership
------------------------

Each area may contain the ``status``, ``maintainers``,
``collaborators``, ``inform``, ``labels``, ``files``,
``files-regex``, ``file-groups`` and ``description`` fields. The
format is documented in the comment at the top of the file.

- ``status`` is one of ``maintained``, ``odd fixes``,
  ``unmaintained`` or ``obsolete``.
- Every tracked file must belong to at least one area; ``just check-maintainers``
  enforces this in CI.
- When a commit adds a file outside the existing areas, update
  ``MAINTAINERS.yml`` in the same commit.

Looking up maintainers
----------------------

``scripts/host/get_maintainer.py`` reads ``MAINTAINERS.yml``. Install its Python
dependencies once:

.. code-block:: bash

   pip install -r scripts/ci/requirements.txt

Then query it through just:

.. code-block:: bash

   just maint-paths scripts/host/cosim_launch.sh tests/   # areas for paths
   just maint-commits origin/main..                  # areas touched by commits
   just maint-areas                                  # all areas and maintainers

``python3 scripts/host/get_maintainer.py --help`` lists the other subcommands, such as
``orphaned`` and ``count``.

Checks
------

.. list-table::
   :header-rows: 1

   * - Check
     - Where
     - Fails when
   * - ``just check-maintainers``
     - ``Maintainers`` job in ``ci.yml``
     - ``MAINTAINERS.yml`` has an unknown key, a bad status, a malformed list,
       a glob that matches no file, a directory glob without a trailing
       ``/``, an invalid regex, or a maintained area without maintainers;
       or a tracked file belongs to no area
   * - ``scripts/ci/check_maintainer_changes.py``
     - ``assigner.yml``
     - A pull request adds a maintainer or collaborator who lacks at least
       triage access to the repository

Automatic assignment
--------------------

``.github/workflows/assigner.yml`` runs ``scripts/ci/set_assignees.py`` when
a pull request to ``main`` is opened, updated, reopened, or marked ready for
review:

- The labels of every affected area are added to the pull request.
- The maintainers and collaborators of every affected area are requested as
  reviewers, except the pull request author and people who removed themselves
  from the review request.
- The maintainers of the area with the most changed files are assigned. If the
  author is the only maintainer of that area, the next area is used.
  ``Documentation`` maintainers are assigned only when no other area is
  affected.
- When ``MAINTAINERS.yml`` changes, the maintainers of every changed area are
  also requested as reviewers.

When an issue is labeled, the maintainers of the area that owns those labels are
assigned to it.

The workflow uses ``pull_request_target`` and runs the scripts from the
``main`` branch. It reads only ``MAINTAINERS.yml`` from the pull request, and
only as data, so pull requests from forks cannot change what the workflow
executes.

Adding a maintainer
-------------------

1. Give the person at least triage access to the GitHub repository.
2. Add their GitHub ID under ``maintainers`` or ``collaborators`` of the area
   in ``MAINTAINERS.yml``.
3. Open a pull request. The current maintainers of that area are requested as
   reviewers, and the access check fails if step 1 was skipped.

Related pages
-------------

- :doc:`workflow`
- :doc:`patch_check`
- :doc:`ci`
