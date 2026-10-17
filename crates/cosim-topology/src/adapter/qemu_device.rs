// SPDX-License-Identifier: Apache-2.0

//! QEMU device models exported through the vfio-user server object.

use std::path::PathBuf;

use anyhow::{Context, Result, bail, ensure};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};

use super::{DeviceContext, Launch, Probe, qemu_path};
use crate::model::{Identifier, MemoryRegion};

/// A QEMU `-machine x-remote` process serving one PCI device.
#[non_exhaustive]
#[derive(Clone, Debug, Serialize)]
pub struct QemuDevice {
    /// QEMU `-device` properties, including `driver` and `id`.
    pub properties: Map<String, Value>,
    /// QEMU device identifier referenced by the vfio-user server.
    pub device_id: String,
    /// Additional QEMU arguments.
    pub extra: Vec<String>,
    /// Output text that must appear before the device is ready.
    pub ready_log: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Arguments {
    device: Map<String, Value>,
    #[serde(default)]
    extra: Vec<String>,
}

impl QemuDevice {
    /// Name of the built-in kind.
    pub(crate) const KIND: &'static str = "qemu-device";
    const DEFAULT_ID: &'static str = "device0";

    pub(crate) fn new(
        config: Option<PathBuf>,
        args: Map<String, Value>,
        regions: &[MemoryRegion],
        ready_log: Option<String>,
    ) -> Result<Self> {
        ensure!(
            config.is_none(),
            "qemu-device accepts device properties through args.device"
        );
        ensure!(
            regions.is_empty(),
            "qemu-device cannot receive private memory regions; use a runtime command template"
        );
        let Arguments { mut device, extra } =
            serde_json::from_value(Value::Object(args)).context("qemu-device args")?;
        ensure!(
            device
                .get("driver")
                .and_then(Value::as_str)
                .is_some_and(|driver| !driver.is_empty()),
            "qemu-device requires args.device.driver"
        );
        let device_id = match device.get("id") {
            None => Self::DEFAULT_ID.to_owned(),
            Some(Value::String(id)) => Identifier::new(id.as_str())?.to_string(),
            Some(_) => bail!("args.device.id must be a string"),
        };
        device.insert("id".to_owned(), Value::String(device_id.clone()));
        Ok(Self {
            properties: device,
            device_id,
            extra,
            ready_log,
        })
    }

    pub(super) fn launch(&self, context: &DeviceContext<'_>) -> Result<Launch> {
        let server = json!({"qom-type": "x-vfio-user-server", "id": "vfio0",
            "socket": {"type": "unix", "path": context.socket}, "device": self.device_id});
        let mut argv = vec![
            "-machine".to_owned(),
            "x-remote,vfio-user=on,auto-shutdown=off".to_owned(),
            "-nodefaults".to_owned(),
            "-display".to_owned(),
            "none".to_owned(),
            "-qmp".to_owned(),
            format!("unix:{},server=on,wait=off", qemu_path(context.qmp)),
            "-device".to_owned(),
            Value::Object(self.properties.clone()).to_string(),
            "-object".to_owned(),
            server.to_string(),
        ];
        argv.extend(self.extra.iter().cloned());
        let mut probes = Vec::new();
        if let Some(marker) = &self.ready_log {
            probes.push(Probe::Log {
                path: context.output_log.to_path_buf(),
                marker: marker.clone(),
                timeout: None,
            });
        }
        probes.extend([
            Probe::Socket {
                path: context.socket.to_path_buf(),
            },
            Probe::Qmp {
                path: context.qmp.to_path_buf(),
            },
        ]);
        Ok(Launch { argv, probes })
    }
}
