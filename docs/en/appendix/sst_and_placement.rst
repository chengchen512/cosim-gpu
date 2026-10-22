.. SPDX-License-Identifier: Apache-2.0

.. _appendix-sst-and-placement:

SST experiments and remote placement
====================================

This page records the data models and current state of the SST configurations in
the repository, and the actual behavior of the remote placement field in a
topology.

SST data models
---------------

``configs/sst/`` holds independent SST (Structural Simulation Toolkit)
experiment configurations:

- ``multi_node_topology.py`` describes the parameters of an SST multi-node
  network;
- ``mi300x_merlin_poc.py`` provides an MI300X integration experiment with
  SST/Merlin.

These configurations depend on the corresponding simulator components and have
interfaces independent of Rust process management. They are not part of the
``cosim run`` launch path, and the launcher does not produce an execution plan
for them.

For multi-GPU interconnect, gem5's ``XGMIBridge`` and related configuration
implement in-simulator interconnect behavior; gem5's Python configuration can also
create multiple GPU objects and their interconnect inside a single gem5 process
through ``--num-gpus``. The YAML MI300X adapter takes a different approach: one GPU
per process, with one VRAM region per GPU.

Remote placement rules
----------------------

The topology ``placement.agent`` field names the remote agent used for
distributed execution. The current executor behaves as follows:

- Remote placement can be described in a configuration, but ``cosim run`` rejects
  it before allocating resources.
- Switch nodes are a reserved design element and are not yet part of the topology
  format.
- The local execution path runs only local processes and establishes no
  cross-machine simulator interconnect.

SST experiments and remote placement are therefore configuration forms that can be
described but not executed by ``cosim run``.

Current state and limitations
-----------------------------

- The SST configurations are an independent experimental path; they cannot be
  executed by ``cosim run`` today and need the corresponding external simulator
  components.
- Multi-machine topologies in the repository expand machine counts inside one host
  through ``count`` and stay on the local execution path; cross-machine simulator
  interconnect is expressed only in the SST configurations.
- The topology format stays conservative about ``placement`` and switch nodes: the
  former is rejected before running, and the latter is not part of the format yet.

Related pages
-------------

- :ref:`sim-gem5-multi-gpu`
- :ref:`topo-write-topology`
- :ref:`ref-topology-schema`
- :ref:`topo-multi-machine`
