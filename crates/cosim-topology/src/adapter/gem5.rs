// SPDX-License-Identifier: Apache-2.0

//! One MI300X GPU simulated by gem5 in each process.

use std::path::PathBuf;

use anyhow::{Context, Result, bail, ensure};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

use super::{DeviceContext, Launch, Probe};
use crate::model::{Device, MemoryRegion, Pci};

/// gem5 `mi300_cosim.py` with a shared memory pool.
#[non_exhaustive]
#[derive(Clone, Debug, Serialize)]
pub struct Gem5Mi300x {
    /// Path to `mi300_cosim.py`.
    pub config: PathBuf,
    /// gem5 debug flags.
    pub debug_flags: Vec<String>,
    /// Number of compute units.
    pub compute_units: u32,
    /// Additional configuration-script arguments.
    pub extra: Vec<String>,
    /// Output text that replaces the default listener message.
    pub ready_log: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Arguments {
    #[serde(default)]
    gem5_debug_flags: Vec<String>,
    num_compute_units: Option<u32>,
    #[serde(default)]
    extra: Vec<String>,
}

impl Gem5Mi300x {
    /// Name of the built-in kind.
    pub(crate) const KIND: &'static str = "gem5-mi300x";
    /// Executable searched in `PATH` when the device omits `runtime.binary`.
    pub(crate) const DEFAULT_BINARY: &'static str = "gem5.opt";
    const VENDOR_ID: u16 = 0x1002;
    const DEVICE_ID: u16 = 0x74a0;
    const MSIX_VECTORS: u16 = 256;
    const DEFAULT_COMPUTE_UNITS: u32 = 40;

    pub(crate) fn new(
        config: Option<PathBuf>,
        args: Map<String, Value>,
        regions: &[MemoryRegion],
        pci: &Pci,
        ready_log: Option<String>,
    ) -> Result<Self> {
        let config = config.context("gem5-mi300x requires config pointing to mi300_cosim.py")?;
        let args: Arguments =
            serde_json::from_value(Value::Object(args)).context("gem5-mi300x args")?;
        let compute_units = args
            .num_compute_units
            .unwrap_or(Self::DEFAULT_COMPUTE_UNITS);
        ensure!(
            (1..=1024).contains(&compute_units),
            "num_compute_units must be 1..1024"
        );
        let [vram] = regions else {
            bail!("gem5-mi300x requires exactly one memory region named vram");
        };
        ensure!(
            vram.name.as_str() == "vram",
            "gem5-mi300x requires exactly one memory region named vram"
        );
        ensure!(
            vram.size.is_power_of_two(),
            "MI300X VRAM must be a power of two"
        );
        ensure!(
            pci.vendor_id.is_none_or(|id| id == Self::VENDOR_ID)
                && pci.device_id.is_none_or(|id| id == Self::DEVICE_ID)
                && pci
                    .msix_vectors
                    .is_none_or(|count| count == Self::MSIX_VECTORS),
            "PCI metadata does not match MI300X"
        );
        Ok(Self {
            config,
            debug_flags: args.gem5_debug_flags,
            compute_units,
            extra: args.extra,
            ready_log,
        })
    }

    pub(super) fn launch(&self, device: &Device, context: &DeviceContext<'_>) -> Result<Launch> {
        let vram = context
            .layout
            .regions_of(&device.id)
            .iter()
            .find(|region| region.name == "vram")
            .context("the memory layout has no vram region")?;
        let mut argv = vec![format!(
            "--outdir={}",
            context.node_dir.join("m5out").display()
        )];
        if !self.debug_flags.is_empty() {
            argv.push(format!("--debug-flags={}", self.debug_flags.join(",")));
        }
        argv.extend([
            "--listener-mode=off".to_owned(),
            self.config.display().to_string(),
            format!("--socket-path={}", context.socket.display()),
            format!("--shared-pool={}", context.pool.display()),
            format!("--pool-vram-offset={}", vram.offset),
            format!("--dgpu-mem-size={}B", vram.size),
            format!("--mem-size={}B", context.layout.ram.size),
            format!(
                "--host-memory-ranges={}",
                serde_json::to_string(&context.layout.guest_ranges)?
            ),
            format!("--num-compute-units={}", self.compute_units),
            "--num-gpus=1".to_owned(),
        ]);
        argv.extend(self.extra.iter().cloned());
        let marker = self.ready_log.clone().unwrap_or_else(|| {
            format!(
                "MI300XVfioUser: listening on {} (vfio-user protocol)",
                context.socket.display()
            )
        });
        Ok(Launch {
            argv,
            probes: vec![
                Probe::Log {
                    path: context.output_log.to_path_buf(),
                    marker,
                    timeout: None,
                },
                Probe::Socket {
                    path: context.socket.to_path_buf(),
                },
            ],
        })
    }
}
