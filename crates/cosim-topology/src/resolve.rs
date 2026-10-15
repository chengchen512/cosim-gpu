// SPDX-License-Identifier: Apache-2.0

//! Converts decoded documents into validated topology values.

use std::collections::{BTreeMap, BTreeSet};
use std::num::NonZeroU32;
use std::path::{Path, PathBuf};
use std::time::Duration;

use anyhow::{Context, Result, bail, ensure};
use serde_json::{Map, Value};

use crate::adapter::{Adapter, CommandTemplate, Gem5Mi300x, QemuDevice, TemplateDevice};
use crate::model::{
    Device, DeviceModel, DirectBoot, Disk, DiskFormat, DiskMode, GuestHints, Host, Identifier,
    Machine, MemoryRegion, Pci, Program, Role, SerialReady, Topology,
};
use crate::raw;
use crate::size::ByteSize;

const MAX_MACHINES: usize = 4096;
const MAX_DEVICES: usize = 256;

/// A decoded machine and the reference name of each device entry.
pub(crate) struct MachineSpec {
    pub(crate) machine: raw::Machine,
    /// The `id` or `use` value written for each device before expansion.
    pub(crate) device_names: Vec<Option<String>>,
}

/// Declared adapter kinds.
pub(crate) struct Kinds(BTreeMap<String, Kind>);

struct Kind {
    role: Role,
    model: DeviceModel,
    command: CommandTemplate,
    max_devices: Option<usize>,
}

impl Kinds {
    pub(crate) fn new(kinds: BTreeMap<String, raw::Kind>) -> Result<Self> {
        kinds
            .into_iter()
            .map(|(name, kind)| {
                Identifier::new(name.as_str()).context("kind name")?;
                let command = CommandTemplate::from_parts(kind.argv, kind.command)
                    .and_then(|command| command.context("one of command or argv is required"))
                    .with_context(|| format!("kind {name}"))?;
                ensure!(
                    kind.max_devices.is_none() || kind.role == Role::Host,
                    "kind {name}: max_devices applies to host kinds"
                );
                let kind = Kind {
                    role: kind.role,
                    model: kind.model,
                    command,
                    max_devices: kind.max_devices,
                };
                Ok((name, kind))
            })
            .collect::<Result<_>>()
            .map(Self)
    }

    fn get(&self, name: &str, role: Role) -> Result<&Kind> {
        let role_name = match role {
            Role::Device => "device",
            Role::Host => "host",
        };
        self.0
            .get(name)
            .filter(|kind| kind.role == role)
            .with_context(|| format!("unknown {role_name} kind {name}"))
    }
}

/// Builds the topology and checks rules that span machines.
pub(crate) fn topology(
    source: PathBuf,
    specs: Vec<MachineSpec>,
    kinds: &Kinds,
) -> Result<Topology> {
    ensure!(
        !specs.is_empty(),
        "topology must contain at least one machine"
    );
    let mut total = 0usize;
    for spec in &specs {
        let count = spec.machine.count.unwrap_or(1);
        ensure!(count > 0, "machine count must be positive");
        total = total.checked_add(count).context("machine count overflow")?;
        ensure!(
            total <= MAX_MACHINES,
            "topology exceeds {MAX_MACHINES} machines"
        );
    }
    let mut machines = Vec::with_capacity(total);
    for spec in specs {
        machines.extend(machine(spec, kinds)?);
    }
    unique(machines.iter().map(|machine| &machine.id), "machine")?;
    disk_sharing(&machines)?;
    Ok(Topology { source, machines })
}

/// One device entry before identifier expansion.
struct DeviceEntry {
    base: String,
    explicit: bool,
    count: usize,
    prototype: DevicePrototype,
}

/// A validated device that has not received its identifier.
struct DevicePrototype {
    kind: String,
    model: DeviceModel,
    adapter: Adapter,
    program: Program,
    regions: Vec<MemoryRegion>,
    pci: Pci,
    guest_hints: GuestHints,
}

impl DevicePrototype {
    fn instance(&self, id: Identifier) -> Device {
        Device {
            id,
            kind: self.kind.clone(),
            model: self.model,
            adapter: self.adapter.clone(),
            program: self.program.clone(),
            regions: self.regions.clone(),
            pci: self.pci.clone(),
            guest_hints: self.guest_hints.clone(),
        }
    }
}

fn machine(spec: MachineSpec, kinds: &Kinds) -> Result<Vec<Machine>> {
    let raw::Machine {
        id,
        count,
        host,
        devices,
        placement,
        ..
    } = spec.machine;
    let id = id
        .filter(|id| !id.is_empty())
        .context("machine id is required")?;
    let expand = || -> Result<Vec<Machine>> {
        let (host, capacity) =
            self::host(host.context("machine has no host")?, kinds).context("host")?;
        let placement = placement
            .map(|placement| {
                ensure!(!placement.agent.is_empty(), "placement.agent is empty");
                Ok(placement.agent)
            })
            .transpose()?;
        let mut entries = Vec::with_capacity(devices.len());
        let mut device_total = 0usize;
        for (device, name) in devices.into_iter().zip(spec.device_names) {
            let count = device.count.unwrap_or(1);
            ensure!(count > 0, "device count must be positive");
            device_total = device_total
                .checked_add(count)
                .context("device count overflow")?;
            ensure!(
                device_total <= capacity,
                "machine exceeds {capacity} devices allowed by host kind {}",
                host.kind
            );
            let explicit = device.id.is_some();
            let base = device
                .id
                .clone()
                .or(name)
                .or_else(|| device.kind.clone())
                .context("device needs an id, use or kind")?;
            let prototype =
                self::device(device, kinds).with_context(|| format!("device {base}"))?;
            entries.push(DeviceEntry {
                base,
                explicit,
                count,
                prototype,
            });
        }
        let devices = instances(entries, &host)?;
        let count = count.unwrap_or(1);
        (0..count)
            .map(|index| {
                let name = if count == 1 {
                    id.clone()
                } else {
                    format!("{id}{index}")
                };
                Ok(Machine {
                    id: Identifier::new(name)?,
                    host: host.clone(),
                    devices: devices.clone(),
                    placement: placement.clone(),
                })
            })
            .collect()
    };
    expand().with_context(|| format!("machine {id}"))
}

/// Assigns device identifiers and checks host constraints.
fn instances(entries: Vec<DeviceEntry>, host: &Host) -> Result<Vec<Device>> {
    let mut ordinals = BTreeMap::<String, usize>::new();
    let mut devices = Vec::new();
    for entry in entries {
        for _ in 0..entry.count {
            let ordinal = ordinals.entry(entry.base.clone()).or_default();
            let name = if entry.explicit && entry.count == 1 {
                entry.base.clone()
            } else {
                format!("{}-{ordinal}", entry.base)
            };
            *ordinal += 1;
            devices.push(entry.prototype.instance(Identifier::new(name)?));
        }
    }
    unique(devices.iter().map(|device| &device.id), "device")?;
    for device in &devices {
        if matches!(device.adapter, Adapter::Gem5Mi300x(_)) {
            ensure!(
                host.memory_map.is_some(),
                "device {}: gem5-mi300x requires host.memory_map",
                device.id
            );
        }
        ensure!(
            device.guest_hints.cmdline.is_none() || host.boot.is_some(),
            "device {}: guest_hints.cmdline requires host boot.kernel",
            device.id
        );
    }
    Ok(devices)
}

fn host(raw: raw::Host, kinds: &Kinds) -> Result<(Host, usize)> {
    let kind_name = raw.kind.context("host.kind is required")?;
    let kind = kinds.get(&kind_name, Role::Host)?;
    ensure!(
        kind.model == DeviceModel::Qemu,
        "host kind {kind_name} must use model: qemu"
    );
    let command = CommandTemplate::from_parts(raw.runtime.argv, raw.runtime.command)
        .context("host.runtime")?
        .unwrap_or_else(|| kind.command.clone());
    let binary = raw
        .runtime
        .binary
        .context("host.runtime.binary is required")?;
    let disks = disks(raw.disks, raw.snapshot)?;
    let host = Host {
        kind: kind_name,
        command,
        program: program(binary, raw.runtime.env)?,
        memory: raw.memory.context("host.memory is required")?,
        memory_align: alignment(raw.memory_align).context("host.memory_align")?,
        memory_map: raw.memory_map.filter(|map| !map.is_empty()),
        cpus: raw
            .cpus
            .and_then(NonZeroU32::new)
            .context("host.cpus must be positive")?,
        accel: required(raw.accel, "host.accel")?,
        machine: required(raw.machine, "host.machine")?,
        cpu: raw.cpu,
        display: raw.display,
        monitor: raw.monitor,
        no_reboot: raw.no_reboot,
        boot: boot(raw.boot)?,
        disks,
        serial_ready: serial(raw.serial)?,
        args: raw.args,
    };
    let capacity = kind.max_devices.unwrap_or(MAX_DEVICES).min(MAX_DEVICES);
    Ok((host, capacity))
}

/// Kinds that a device may reference.
enum DeviceKind<'a> {
    Gem5Mi300x,
    QemuDevice,
    Declared(&'a Kind),
}

fn device(raw: raw::Device, kinds: &Kinds) -> Result<DevicePrototype> {
    let kind_name = raw.kind.context("device kind is required")?;
    let kind = match kind_name.as_str() {
        Gem5Mi300x::KIND => DeviceKind::Gem5Mi300x,
        QemuDevice::KIND => DeviceKind::QemuDevice,
        name => DeviceKind::Declared(kinds.get(name, Role::Device)?),
    };
    let model = match kind {
        DeviceKind::Gem5Mi300x => DeviceModel::Gem5,
        DeviceKind::QemuDevice => DeviceModel::Qemu,
        DeviceKind::Declared(kind) => kind.model,
    };
    let ready_log = raw
        .ready_log
        .map(|marker| {
            ensure!(
                !marker.is_empty() && !marker.contains('\0'),
                "ready_log must be nonempty text without NUL"
            );
            Ok(marker)
        })
        .transpose()?;
    if let Some(vectors) = raw.pci.msix_vectors {
        ensure!(
            (1..=2048).contains(&vectors),
            "msix_vectors must be 1..2048"
        );
    }
    let regions = regions(raw.memory_regions)?;
    let command =
        CommandTemplate::from_parts(raw.runtime.argv, raw.runtime.command).context("runtime")?;
    let adapter = match (command, kind) {
        (Some(command), _) => template_device(command, ready_log, raw.config, raw.args)?,
        (None, DeviceKind::Gem5Mi300x) => Adapter::Gem5Mi300x(Gem5Mi300x::new(
            raw.config, raw.args, &regions, &raw.pci, ready_log,
        )?),
        (None, DeviceKind::QemuDevice) => {
            Adapter::QemuDevice(QemuDevice::new(raw.config, raw.args, &regions, ready_log)?)
        }
        (None, DeviceKind::Declared(kind)) => {
            template_device(kind.command.clone(), ready_log, raw.config, raw.args)?
        }
    };
    let binary = match (raw.runtime.binary, &adapter) {
        (Some(binary), _) => binary,
        (None, Adapter::Gem5Mi300x(_)) => Gem5Mi300x::DEFAULT_BINARY.to_owned(),
        (None, _) => bail!("runtime.binary is required"),
    };
    Ok(DevicePrototype {
        kind: kind_name,
        model,
        adapter,
        program: program(binary, raw.runtime.env)?,
        regions,
        pci: raw.pci,
        guest_hints: raw.guest_hints,
    })
}

fn template_device(
    command: CommandTemplate,
    ready_log: Option<String>,
    config: Option<PathBuf>,
    args: Map<String, Value>,
) -> Result<Adapter> {
    let ready_log = ready_log.context("custom device commands require ready_log")?;
    Ok(Adapter::Template(TemplateDevice {
        command,
        ready_log,
        config,
        args,
    }))
}
fn program(binary: String, env: BTreeMap<String, String>) -> Result<Program> {
    ensure!(
        !binary.is_empty() && !binary.contains('\0'),
        "runtime.binary must be nonempty text without NUL"
    );
    for (name, value) in &env {
        ensure!(
            !name.is_empty() && !name.contains(['=', '\0']) && !value.contains('\0'),
            "runtime.env requires nonempty names without '=' or NUL and values without NUL"
        );
    }
    Ok(Program { binary, env })
}

fn regions(raw: Vec<raw::MemoryRegion>) -> Result<Vec<MemoryRegion>> {
    let regions = raw
        .into_iter()
        .map(|region| {
            let name = Identifier::new(region.name)?;
            let align = alignment(region.align).with_context(|| format!("region {name}"))?;
            Ok(MemoryRegion {
                name,
                size: region.size,
                align,
            })
        })
        .collect::<Result<Vec<_>>>()?;
    unique(regions.iter().map(|region| &region.name), "memory region")?;
    Ok(regions)
}

fn alignment(value: Option<ByteSize>) -> Result<ByteSize> {
    let align = value.unwrap_or(ByteSize::TWO_MEBIBYTES);
    ensure!(align.is_power_of_two(), "alignment must be a power of two");
    Ok(align)
}

fn required(value: Option<String>, field: &str) -> Result<String> {
    value
        .filter(|value| !value.is_empty())
        .with_context(|| format!("{field} is required"))
}

fn boot(raw: raw::Boot) -> Result<Option<DirectBoot>> {
    let Some(kernel) = raw.kernel else {
        ensure!(
            raw.initrd.is_none() && raw.cmdline.is_none(),
            "boot.initrd and boot.cmdline require boot.kernel"
        );
        return Ok(None);
    };
    Ok(Some(DirectBoot {
        kernel,
        initrd: raw.initrd,
        cmdline: raw.cmdline,
    }))
}

fn serial(raw: raw::Serial) -> Result<Option<SerialReady>> {
    let Some(marker) = raw.wait_for else {
        ensure!(
            raw.timeout.is_none(),
            "serial.timeout requires serial.wait_for"
        );
        return Ok(None);
    };
    ensure!(
        !marker.is_empty() && !marker.contains('\0'),
        "serial.wait_for must be nonempty text without NUL"
    );
    let timeout = raw
        .timeout
        .map(|seconds| {
            ensure!(
                (1..=86_400).contains(&seconds),
                "serial.timeout must be 1..86400 seconds"
            );
            Ok(Duration::from_secs(seconds))
        })
        .transpose()?;
    Ok(Some(SerialReady { marker, timeout }))
}

fn disks(raw: Vec<raw::Disk>, snapshot: bool) -> Result<Vec<Disk>> {
    let disks = raw
        .into_iter()
        .map(|disk| self::disk(disk, snapshot))
        .collect::<Result<Vec<_>>>()?;
    unique(disks.iter().map(|disk| &disk.id), "disk")?;
    ensure!(
        disks.iter().filter(|disk| disk.boot).count() <= 1,
        "only one disk can have boot: true"
    );
    Ok(disks)
}

fn disk(raw: raw::Disk, snapshot: bool) -> Result<Disk> {
    let id = Identifier::new(raw.id)?;
    let decode = || -> Result<Disk> {
        let backing = raw.backing.is_some();
        let (source, create) = match (raw.path, raw.backing) {
            (Some(path), None) if raw.create => {
                let size = raw.size.context("create: true requires size")?;
                (path, Some(size))
            }
            (Some(path), None) => {
                ensure!(raw.size.is_none(), "size requires create: true");
                (path, None)
            }
            (None, Some(backing)) => {
                ensure!(
                    !raw.create && raw.size.is_none(),
                    "create and size require path"
                );
                (backing, None)
            }
            _ => bail!("exactly one of path or backing is required"),
        };
        let mode = match (raw.readonly, raw.shared) {
            (Some(true), _) => DiskMode::ReadOnly,
            (_, Some(true)) => bail!("shared disks must be readonly"),
            (Some(false), Some(false)) if !backing && !snapshot => DiskMode::Direct,
            (Some(false), Some(false)) | (None, _) => DiskMode::Overlay,
            (Some(false), None) => {
                bail!("direct writes require readonly: false and shared: false")
            }
        };
        Ok(Disk {
            id: id.clone(),
            source,
            format: raw.format,
            bus: raw.bus,
            boot: raw.boot,
            mode,
            create,
        })
    };
    decode().with_context(|| format!("disk {id}"))
}

/// Rejects identifiers that differ only in ASCII case.
fn unique<'a>(ids: impl Iterator<Item = &'a Identifier>, what: &str) -> Result<()> {
    let mut seen = BTreeSet::new();
    for id in ids {
        ensure!(seen.insert(id.folded()), "duplicate {what} {id}");
    }
    Ok(())
}

/// Rejects direct writers that share an image and conflicting creation requests.
fn disk_sharing(machines: &[Machine]) -> Result<()> {
    let mut users = BTreeMap::<&Path, Vec<(&Identifier, DiskMode)>>::new();
    let mut created = BTreeMap::<&Path, (ByteSize, DiskFormat)>::new();
    for machine in machines {
        for disk in &machine.host.disks {
            users
                .entry(&disk.source)
                .or_default()
                .push((&machine.id, disk.mode));
            if let Some(size) = disk.create {
                let request = (size, disk.format);
                let previous = *created.entry(&disk.source).or_insert(request);
                ensure!(
                    previous == request,
                    "conflicting creation size or format for {}",
                    disk.source.display()
                );
            }
        }
    }
    for (source, users) in users {
        let direct = users.iter().any(|(_, mode)| *mode == DiskMode::Direct);
        if direct && users.len() > 1 {
            let names = users
                .iter()
                .map(|(machine, _)| machine.as_str())
                .collect::<Vec<_>>()
                .join(", ");
            bail!(
                "{} is written directly while other disks use it ({names})",
                source.display()
            );
        }
    }
    Ok(())
}
