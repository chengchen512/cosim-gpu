// SPDX-License-Identifier: Apache-2.0

//! Readiness conditions evaluated after a process starts.

use std::os::unix::fs::FileTypeExt;
use std::path::Path;
use std::time::Duration;

use anyhow::{Context, Result, ensure};
use cosim_topology::Probe;
use serde_json::Value;
use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;
use tokio::time::{self, Instant};

const POLL_INTERVAL: Duration = Duration::from_millis(25);
const LOG_CHUNK: usize = 64 * 1024;

/// Evaluates probes in order; each deadline is measured from `started`.
pub(crate) async fn wait_all(
    probes: &[Probe],
    started: Instant,
    ready_timeout: Duration,
) -> Result<()> {
    for probe in probes {
        let timeout = match probe {
            Probe::Log {
                timeout: Some(timeout),
                ..
            } => *timeout,
            _ => ready_timeout,
        };
        let deadline = started
            .checked_add(timeout)
            .context("readiness deadline overflow")?;
        time::timeout_at(deadline, wait(probe))
            .await
            .with_context(|| format!("readiness timed out: {}", describe(probe)))??;
    }
    Ok(())
}

fn describe(probe: &Probe) -> String {
    match probe {
        Probe::Log { path, marker, .. } => format!("{marker:?} in {}", path.display()),
        Probe::Socket { path } => format!("socket {}", path.display()),
        Probe::Qmp { path } => format!("QMP negotiation on {}", path.display()),
    }
}

async fn wait(probe: &Probe) -> Result<()> {
    match probe {
        Probe::Log { path, marker, .. } => log(path, marker).await,
        Probe::Socket { path } => socket(path).await,
        Probe::Qmp { path } => qmp(path).await,
    }
}

/// Reads an append-only log in bounded chunks until it contains `marker`.
///
/// Text that may hold the start of the marker is kept across reads.
async fn log(path: &Path, marker: &str) -> Result<()> {
    ensure!(!marker.is_empty(), "log markers must not be empty");
    let marker = marker.as_bytes();
    let mut file = None;
    let mut chunk = vec![0; LOG_CHUNK];
    let mut pending = Vec::with_capacity(LOG_CHUNK + marker.len());
    loop {
        if file.is_none() {
            file = match tokio::fs::File::open(path).await {
                Ok(file) => Some(file),
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => None,
                Err(error) => {
                    return Err(error).with_context(|| format!("read {}", path.display()));
                }
            };
        }
        let count = match &mut file {
            Some(file) => file.read(&mut chunk).await?,
            None => 0,
        };
        pending.extend_from_slice(&chunk[..count]);
        if pending.windows(marker.len()).any(|window| window == marker) {
            return Ok(());
        }
        let consumed = pending.len().saturating_sub(marker.len() - 1);
        pending.drain(..consumed);
        if count == 0 {
            time::sleep(POLL_INTERVAL).await;
        }
    }
}

/// Waits until `path` is a Unix socket without connecting to it.
async fn socket(path: &Path) -> Result<()> {
    loop {
        match tokio::fs::symlink_metadata(path).await {
            Ok(metadata) if metadata.file_type().is_socket() => return Ok(()),
            Ok(_) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(error).with_context(|| format!("inspect {}", path.display())),
        }
        time::sleep(POLL_INTERVAL).await;
    }
}

/// Connects to a QMP server and negotiates capabilities.
async fn qmp(path: &Path) -> Result<()> {
    let stream = loop {
        match UnixStream::connect(path).await {
            Ok(stream) => break stream,
            Err(error)
                if matches!(
                    error.kind(),
                    std::io::ErrorKind::NotFound | std::io::ErrorKind::ConnectionRefused
                ) =>
            {
                time::sleep(POLL_INTERVAL).await;
            }
            Err(error) => {
                return Err(error).with_context(|| format!("connect {}", path.display()));
            }
        }
    };
    let mut connection = BufReader::new(stream);
    let mut line = String::new();
    connection.read_line(&mut line).await?;
    let greeting: Value = serde_json::from_str(&line).context("QMP greeting")?;
    ensure!(greeting.get("QMP").is_some(), "invalid QMP greeting");
    connection
        .get_mut()
        .write_all(b"{\"execute\":\"qmp_capabilities\",\"id\":\"cosim-ready\"}\n")
        .await?;
    loop {
        line.clear();
        ensure!(
            connection.read_line(&mut line).await? > 0,
            "QMP closed during capability negotiation"
        );
        let message: Value = serde_json::from_str(&line).context("QMP message")?;
        if message.get("id").and_then(Value::as_str) == Some("cosim-ready") {
            ensure!(
                message.get("return").is_some(),
                "QMP rejected capabilities: {message}"
            );
            return Ok(());
        }
    }
}
