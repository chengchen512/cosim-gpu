// SPDX-License-Identifier: Apache-2.0

//! Native process groups owned by a session.

use std::collections::BTreeMap;
use std::fmt;
use std::fs::File;
use std::os::fd::BorrowedFd;
use std::path::{Path, PathBuf};
use std::process::{ExitStatus, Stdio};
use std::time::Duration;

use anyhow::{Context, Result, ensure};
use command_fds::CommandFdExt;
use nix::errno::Errno;
use nix::sys::signal::{self, Signal};
use nix::unistd::Pid;
use tokio::process::{Child, Command};
use tokio::time::{self, Instant};
use tokio_util::sync::CancellationToken;

use crate::plan;

/// Time a process group has to exit after SIGTERM.
const GRACE_PERIOD: Duration = Duration::from_secs(5);
/// Time to confirm that a process group disappeared after SIGKILL.
const KILL_PERIOD: Duration = Duration::from_secs(1);
const POLL_INTERVAL: Duration = Duration::from_millis(10);

/// Starts children that the kernel kills when the launcher dies.
///
/// On Linux, `setpriv --pdeathsig KILL` sets the parent-death signal before
/// it executes the program. The signal follows the thread that created the
/// child, so children are spawned from the long-lived runtime thread.
#[derive(Clone, Debug)]
pub(crate) struct Lifeline {
    setpriv: PathBuf,
}

impl Lifeline {
    /// Locates `setpriv` and rejects systems without parent-death signals.
    pub(crate) fn locate(search_path: &str) -> Result<Self> {
        ensure!(
            cfg!(target_os = "linux"),
            "cosim run requires Linux; set COSIM_ENV=container to use the development container"
        );
        let setpriv = plan::resolve_program("setpriv", search_path)
            .context("cosim run requires setpriv from util-linux")?;
        Ok(Self { setpriv })
    }
}

/// What a process receives when it starts.
pub(crate) struct Spawn<'a> {
    pub(crate) program: &'a Path,
    pub(crate) argv: &'a [String],
    pub(crate) env: &'a BTreeMap<String, String>,
    pub(crate) directory: &'a Path,
    pub(crate) log: &'a Path,
    /// Lock descriptors the process keeps at their current numbers.
    pub(crate) inherit: &'a [BorrowedFd<'a>],
}

/// A child process leading its own process group.
///
/// Dropping an unstopped group sends SIGKILL to every member. Use
/// [`ProcessGroup::shutdown`] for graceful termination.
pub(crate) struct ProcessGroup {
    child: Child,
    group: Pid,
    armed: bool,
}

impl ProcessGroup {
    /// Starts a process in a new group with output appended to `spawn.log`.
    ///
    /// Only the descriptors in `spawn.inherit` stay open across `exec`, so
    /// concurrent sessions in one launcher do not share their locks.
    pub(crate) fn spawn(lifeline: &Lifeline, spawn: &Spawn<'_>) -> Result<Self> {
        let log = File::options()
            .create(true)
            .append(true)
            .open(spawn.log)
            .with_context(|| format!("open {}", spawn.log.display()))?;
        let inherit = spawn
            .inherit
            .iter()
            .map(BorrowedFd::try_clone_to_owned)
            .collect::<std::io::Result<Vec<_>>>()
            .context("duplicate lock descriptors")?;
        let mut command = Command::new(&lifeline.setpriv);
        command
            .args(["--pdeathsig", "KILL", "--"])
            .arg(spawn.program)
            .args(spawn.argv)
            .env_clear()
            .envs(spawn.env)
            .current_dir(spawn.directory)
            .stdin(Stdio::null())
            .stdout(log.try_clone()?)
            .stderr(log)
            .process_group(0)
            .preserved_fds(inherit);
        let child = command
            .spawn()
            .with_context(|| format!("start {}", spawn.program.display()))?;
        let id = child.id().context("the child has no process ID")?;
        let group = Pid::from_raw(i32::try_from(id).context("process ID out of range")?);
        Ok(Self {
            child,
            group,
            armed: true,
        })
    }

    /// Waits for the group leader to exit. Cancelling the wait is safe.
    pub(crate) async fn wait(&mut self) -> Result<ExitStatus> {
        self.child.wait().await.context("wait for child")
    }

    /// Collects an available status without waiting for an I/O notification.
    pub(crate) fn try_wait(&mut self) -> Result<Option<ExitStatus>> {
        self.child.try_wait().context("query child status")
    }

    /// Sends SIGTERM, waits for the group, then sends SIGKILL to survivors.
    ///
    /// `force` skips the remaining grace period. An error carries
    /// [`Unconfirmed`]: shared resources must then be kept.
    pub(crate) async fn shutdown(mut self, force: &CancellationToken) -> Result<()> {
        let result = self.terminate(force).await;
        if result.is_ok() {
            self.armed = false;
        }
        result.map_err(|error| error.context(Unconfirmed))
    }

    async fn terminate(&mut self, force: &CancellationToken) -> Result<()> {
        let group = self.group;
        signal_group(group, Signal::SIGTERM)?;
        let graceful = async {
            self.child.wait().await?;
            while group_exists(group)? {
                time::sleep(POLL_INTERVAL).await;
            }
            anyhow::Ok(())
        };
        tokio::select! {
            result = time::timeout(GRACE_PERIOD, graceful) => {
                if let Ok(result) = result {
                    result?;
                }
            }
            _ = force.cancelled() => {}
        }
        if group_exists(group)? {
            signal_group(group, Signal::SIGKILL)?;
        }
        time::timeout(KILL_PERIOD, self.child.wait())
            .await
            .context("the child did not exit after SIGKILL")??;
        let deadline = Instant::now() + KILL_PERIOD;
        while group_exists(group)? && Instant::now() < deadline {
            time::sleep(POLL_INTERVAL).await;
        }
        ensure!(
            !group_exists(group)?,
            "process group {group} still exists after SIGKILL"
        );
        Ok(())
    }
}

/// Marks errors after which a process group may still be running.
#[derive(Debug)]
pub(crate) struct Unconfirmed;

impl fmt::Display for Unconfirmed {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("process termination could not be confirmed")
    }
}

/// Returns whether an error leaves process termination unconfirmed.
pub(crate) fn unconfirmed(error: &anyhow::Error) -> bool {
    error.downcast_ref::<Unconfirmed>().is_some()
}

impl Drop for ProcessGroup {
    fn drop(&mut self) {
        if self.armed {
            let _ = signal::killpg(self.group, Signal::SIGKILL);
        }
    }
}

fn signal_group(group: Pid, signal: Signal) -> Result<()> {
    match signal::killpg(group, signal) {
        Ok(()) | Err(Errno::ESRCH) => Ok(()),
        Err(error) => Err(error).with_context(|| format!("send {signal} to process group {group}")),
    }
}

fn group_exists(group: Pid) -> Result<bool> {
    match signal::killpg(group, None) {
        Ok(()) => Ok(true),
        Err(Errno::ESRCH) => Ok(false),
        Err(error) => Err(error).with_context(|| format!("inspect process group {group}")),
    }
}
