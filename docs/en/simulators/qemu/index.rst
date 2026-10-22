.. SPDX-License-Identifier: Apache-2.0

.. _sim-qemu-index:

QEMU roles
===========

QEMU appears in this project as two different processes: the vhost that runs the guest, and a functional model that exports a PCI device. They have independent command lines and lifetimes.

Role One: vhost
----------------

The host QEMU runs guest Linux, the amdgpu driver and ROCm applications. It owns CPU, memory, the PCIe topology, direct kernel boot, and QMP and serial management. It maps the machine memory pool as guest RAM and attaches every device as a separate vfio-user client on a dedicated PCIe root port.

Role Two: device model
-----------------------

The device QEMU uses ``-machine x-remote`` and ``x-vfio-user-server`` to export one PCI device, for example the ``edu`` educational device shipped with QEMU. This mode is functional only; it suits protocol, driver and integration tests and provides no timing model.

Chapter Contents
-----------------

.. toctree::
   :maxdepth: 1

   vhost
   device_models

Recommended Reading Path
-------------------------

- Read :doc:`vhost` first for the guest runtime setup.
- Then read :doc:`device_models` for the vfio-user functional device startup.
- For MI300X performance behavior, continue with :doc:`../gem5/index`.
- For the system view of the connection protocol, see :ref:`arch-vfio-user`.
