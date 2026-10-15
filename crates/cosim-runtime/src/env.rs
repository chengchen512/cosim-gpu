// SPDX-License-Identifier: Apache-2.0

//! Facts about the executing system that a plan records.

use std::ffi::OsStr;
use std::path::PathBuf;

use anyhow::{Context, Result};
use cosim_topology::PageSize;
use nix::unistd::{self, SysconfVar, User};
use serde::Serialize;

use crate::layout;

/// Host facts used to plan and run a session.
#[non_exhaustive]
#[derive(Clone, Debug, Serialize)]
pub struct ExecEnv {
    /// Memory page size used for pool layouts.
    pub page_size: PageSize,
    /// Absolute `PATH` for processes that do not set their own.
    pub search_path: String,
    /// Directory of image locks shared by cooperating sessions.
    pub disk_lock_dir: PathBuf,
}

impl ExecEnv {
    /// Reads the page size, `PATH`, `COSIM_DISK_LOCK_DIR` and the account home.
    pub fn local() -> Result<Self> {
        let search_path = absolute_search_path(&std::env::var_os("PATH").unwrap_or_default())?;
        let disk_lock_dir = match std::env::var_os("COSIM_DISK_LOCK_DIR") {
            Some(directory) => PathBuf::from(directory),
            None => User::from_uid(unistd::geteuid())?
                .context("set COSIM_DISK_LOCK_DIR when the current user has no account entry")?
                .dir
                .join(".cache/cosim-gpu/disk-locks"),
        };
        Ok(Self {
            page_size: page_size()?,
            search_path,
            disk_lock_dir: layout::resolve(&disk_lock_dir)?,
        })
    }
}

/// Returns the memory page size of this system.
pub fn page_size() -> Result<PageSize> {
    let bytes = unistd::sysconf(SysconfVar::PAGE_SIZE)
        .context("query page size")?
        .context("page size is unavailable")?;
    PageSize::new(u64::try_from(bytes).context("invalid page size")?)
}

/// Converts `PATH` entries to absolute directories.
pub(crate) fn absolute_search_path(path: &OsStr) -> Result<String> {
    let directories = std::env::split_paths(path)
        .map(std::path::absolute)
        .collect::<std::io::Result<Vec<_>>>()?;
    std::env::join_paths(directories)?
        .into_string()
        .map_err(|_| anyhow::anyhow!("PATH must be valid UTF-8"))
}
