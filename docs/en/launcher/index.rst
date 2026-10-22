.. SPDX-License-Identifier: Apache-2.0

.. _launcher-index:

Cosim Launcher
===============

This chapter introduces the Cosim Launcher: what it owns, how it is split into crates, and how to read the pages that follow.

The launcher is the Rust ``cosim`` program. It reads a YAML topology, resolves it into a plan for the local system, starts and supervises the host QEMU process and the device processes, and writes a verdict. Three crates separate the concerns: ``cosim-topology``, ``cosim-runtime`` and ``cosim-cli``.

What the Launcher Does
-----------------------

- Load: read YAML documents, expand imports and templates, validate them and compute memory layouts (see :doc:`yaml_pipeline`).
- Plan: combine host facts such as the page size, ``PATH`` and session directories into processes, arguments, readiness probes and resource paths.
- Run: start processes in dependency order, run readiness probes, coordinate shutdown with leases and escalate signals.
- Finish: write the verdict and remove session resources; ``cosim clean`` recovers resources left by an abnormally terminated launcher.

Chapter Contents
-----------------

.. toctree::
   :maxdepth: 1

   cli
   yaml_pipeline
   session_lifecycle
   rust_workspace
   debugging_sessions
   legacy_launcher

Recommended Reading Path
-------------------------

- First use: read :doc:`cli`, then :doc:`yaml_pipeline` to see how input documents become a plan.
- Startup or shutdown failures: :doc:`session_lifecycle` and :doc:`debugging_sessions`.
- Launcher development: :doc:`rust_workspace` covers the crate split and adapter extension points.
- Legacy scripts: :doc:`legacy_launcher` describes the old path and its boundaries.

Related Chapters
-----------------

- :ref:`arch-execution-flow` for the system view of session execution.
- :ref:`arch-components` for the place of each component in the architecture.
- :ref:`ref-device-adapters` for device adapter fields and readiness constraints.
- :ref:`gs-first-session` to run a first session from scratch.
