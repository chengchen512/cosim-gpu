.. SPDX-License-Identifier: Apache-2.0

.. _appendix-standalone-gem5:

Standalone gem5 simulation
==========================

This page describes full-system simulation that runs both CPU and GPU inside gem5
without QEMU, and contrasts it with co-simulation. It is an alternative workflow;
day-to-day development still uses co-simulation.

Differences from co-simulation
------------------------------

.. list-table::
   :header-rows: 1

   * - Aspect
     - Co-simulation (QEMU + gem5)
     - Standalone gem5
   * - CPU execution
     - KVM, close to native speed
     - gem5 atomic/timing models
   * - Boot time
     - about 30 seconds
     - about 2 to 5 minutes (KVM fast-forward)
   * - GPU model
     - gem5 MI300X, exported over vfio-user
     - the same gem5 MI300X model
   * - Driver load
     - ``cosim-gpu-setup.service`` or manual ``modprobe``
     - automated through ``m5 readfile``
   * - Use case
     - driver development, interactive debugging
     - microarchitecture research, performance benchmarking

Quick start
-----------

1. Build gem5 and the guest disk image, following the same steps as
   co-simulation. See :ref:`gs-install` and :ref:`gs-guest-image`.
2. Build the GPU test application:

   .. code-block:: bash

      just build-gpu-app square

3. Run the simulation:

   .. code-block:: bash

      just run-gem5-fs build/apps/square/square.default

   .. warning::

      The ``--app`` argument is mandatory. Without it,
      ``readfile_contents`` is an empty string and the driver is never loaded.

4. Monitor the output:

   .. code-block:: bash

      tail -f m5out/board.pc.com_1.device

The simulation uses KVM to fast-forward the Linux boot, then loads the GPU driver
automatically and runs the given application. The guest calls ``m5 exit`` when
the test finishes, which ends the simulation.

m5 and guest automation
-----------------------

The guest image contains the ``/sbin/m5`` utility and the driver load script
``/home/gem5/load_amdgpu.sh``. gem5 injects the host-side application binary and
command line into guest memory through ``readfile``; the guest script reads
them, loads the amdgpu driver, runs the test, and finally tells the simulator to
exit with ``m5 exit``.

- The application passed with ``--app`` becomes the content of
  ``readfile_contents``.
- The guest script calls ``m5 exit`` after the application exits; otherwise the
  simulator keeps running.
- Output is written under ``m5out/``; the serial log is
  ``board.pc.com_1.device``.

Limitations
-----------

- This path uses gem5's CPU models and does not provide the interactive guest
  environment of QEMU/KVM; both boot and debugging are slower than co-simulation.
- The sample flow uses the ``square`` application as its entry point; a different
  application must be rebuilt and passed as the corresponding ``--app`` path.
- The alternative ``gpufs`` configuration, disk-image validation with
  ``guestfish`` and build internals are out of scope for this page; see the gem5
  GPUFS documentation:
  https://www.gem5.org/documentation/general_docs/gpu_models/gpufs

Related pages
-------------

- :ref:`arch-index`
- :ref:`sim-gem5-index`
- :ref:`sim-guest-driver`
- :ref:`appendix-sst-and-placement`
