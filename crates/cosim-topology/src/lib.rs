// SPDX-License-Identifier: Apache-2.0

//! Loads YAML topology descriptions into validated values.
//!
//! The crate reads only topology documents. Values that depend on the
//! executing system, such as page size, `PATH` and session paths, are
//! supplied by callers through [`PageSize`], [`DeviceContext`] and
//! [`HostContext`].

mod adapter;
mod graph;
mod layout;
mod loader;
mod model;
mod raw;
mod resolve;
mod size;

pub use adapter::{
    Adapter, CommandTemplate, DeviceContext, Gem5Mi300x, HostContext, HostDevice, HostDisk, Launch,
    Probe, QemuDevice, TemplateDevice,
};
pub use graph::graph;
pub use layout::{DeviceRegions, GuestRange, MemoryLayout, PageSize, Region};
pub use loader::load;
pub use model::{
    Device, DeviceModel, DirectBoot, Disk, DiskBus, DiskFormat, DiskMode, GuestHints, Host,
    Identifier, Machine, MemoryRegion, Pci, Program, Role, SerialReady, Topology,
};
pub use size::ByteSize;

/// Generates the JSON Schema of topology documents.
pub fn schema() -> schemars::Schema {
    schemars::schema_for!(raw::Document)
}
