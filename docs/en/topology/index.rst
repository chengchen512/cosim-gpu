.. SPDX-License-Identifier: Apache-2.0


.. _topo-index:

Topology and hardware support
=============================

This chapter answers three questions: which combinations a topology YAML document can describe, which machines (boards) in the repository can be run directly, and which host profiles, devices and payload each machine uses. The topology itself describes hardware and process composition only; guest boot inputs live in a separate payload document.

Three layers
------------

.. list-table::
   :header-rows: 1

   * - Layer
     - Question
     - Page
   * - Topology family
     - Does one YAML document describe one machine or several?
     - :doc:`single_machine`, :doc:`multi_machine`
   * - Machine (board)
     - Which "host + device + pool" combination can be run?
     - :doc:`machines/index`
   * - Components
     - What do host profiles, device models and payloads accept?
     - :doc:`hosts/index`, :doc:`devices/index`, :doc:`payloads/index`

.. mermaid::

   flowchart TD
       T[Topology family] --> M[Machine / board]
       M --> H[Host profile]
       M --> D[Device]
       M --> P[Payload]

In this chapter
---------------

.. toctree::
   :maxdepth: 1

   single_machine
   multi_machine
   write_topology
   machines/index
   hosts/index
   devices/index
   payloads/index

Recommended reading path
------------------------

- New to the project: :doc:`single_machine` → :doc:`machines/index` → :doc:`machines/single_gpu` → :doc:`payloads/index`.
- Writing your own topology: read :doc:`write_topology` first, then copy and edit a sample from :doc:`machines/index`.
- Multi-GPU or mixed devices: :doc:`machines/gpu_8`, :doc:`machines/mixed_models`.
- Several machines in one session: :doc:`multi_machine`.
- Complete host and device fields: :doc:`hosts/index`, :doc:`devices/index`, plus :ref:`ref-topology-schema` and :ref:`ref-device-adapters`.

Related pages
-------------

- First session and commands: :ref:`gs-first-session`, :ref:`launcher-cli`
- Memory pool and vfio-user: :ref:`arch-memory-model`, :ref:`arch-vfio-user`
- Device model details: :ref:`sim-qemu-index`, :ref:`sim-gem5-index`
