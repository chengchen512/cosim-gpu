.. SPDX-License-Identifier: Apache-2.0

.. _gs-index:

Getting Started
===============

This chapter starts from a clean checkout and walks through the host check,
component builds, guest assets, the first co-simulation session, and the
verification inside the guest.

What this chapter covers
------------------------

.. toctree::
   :maxdepth: 1

   requirements
   install
   guest_image
   first_session
   verify_guest
   platforms/linux
   platforms/container
   next_steps

Recommended path
----------------

- First time: follow :doc:`requirements`, :doc:`install`, :doc:`guest_image`,
  :doc:`first_session` and :doc:`verify_guest` in that order.
- Guest assets already built: start with :doc:`first_session`.
- On macOS or Windows: read :doc:`platforms/container` first, then follow the
  same order. A bootable KVM guest still needs a Linux host and KVM.
- Interested in platform details and dependencies: read
  :doc:`platforms/linux` or :doc:`platforms/container`.

Expectations
------------

.. list-table::
   :header-rows: 1

   * - Item
     - Expectation
   * - Disk
     - About 120 GB free: the guest image is about 55 GB plus build artifacts
   * - Memory
     - 16 GB or more; use ``just build-gem5 1`` if linking runs out of memory
   * - First build
     - Tens of minutes to hours, depending on CPU count and cache state
   * - First session
     - A few minutes to a ready GPU; the setup service alone takes about 40 s
   * - Artifact locations
     - Build outputs under ``build/``, session directories under ``.cosim/``

.. tip::

   All build, launch and check tasks are recipes in the top-level
   ``justfile``. Run ``just --list`` for the complete list.

Related pages
-------------

- :doc:`requirements`
- :doc:`first_session`
- :ref:`Architecture overview <arch-index>`
- :ref:`Cosim Launcher <launcher-index>`
