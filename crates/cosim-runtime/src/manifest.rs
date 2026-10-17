// SPDX-License-Identifier: Apache-2.0

//! The persisted resource list and cleanup after the launcher stops.

use std::fs;
use std::io::ErrorKind;
use std::path::{Component, Path, PathBuf};

use anyhow::{Context, Result, bail, ensure};
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};

use crate::layout::SessionLayout;
use crate::plan::Plan;
use crate::resource::{Endpoint, OwnedDir, OwnedFile, RunLock};

const VERSION: u32 = 1;

/// Paths a session may create, written before it creates them.
///
/// A running launcher releases its resources through ownership. The
/// manifest serves `cosim clean` after the launcher itself was killed.
#[derive(Deserialize, Serialize)]
pub(crate) struct Manifest {
    version: u32,
    token: String,
    layout: SessionLayout,
    pools: Vec<PathBuf>,
    overlays: Vec<PathBuf>,
    endpoints: Vec<PathBuf>,
    /// Images being formatted under a temporary name beside their source.
    temporaries: Vec<PathBuf>,
}

impl Manifest {
    pub(crate) fn new(plan: &Plan, token: &str) -> Result<Self> {
        let disks = || plan.machines.iter().flat_map(|machine| &machine.disks);
        let temporaries = disks()
            .filter(|disk| disk.create.is_some())
            .map(|disk| SessionLayout::temporary_image(&disk.source, token))
            .collect::<Result<_>>()?;
        Ok(Self {
            version: VERSION,
            token: token.to_owned(),
            layout: plan.layout.clone(),
            pools: plan
                .machines
                .iter()
                .map(|machine| machine.pool.clone())
                .collect(),
            overlays: disks()
                .filter(|disk| disk.target != disk.source)
                .map(|disk| disk.target.clone())
                .collect(),
            endpoints: plan
                .processes
                .iter()
                .flat_map(|process| process.endpoints.iter().cloned())
                .collect(),
            temporaries,
        })
    }
}

/// Removes the resources of a stopped session and keeps its logs.
///
/// Every session process inherits the session lock, so acquiring it proves
/// that the launcher and all of its processes have exited.
pub fn clean(run_dir: &Path) -> Result<()> {
    let run_dir =
        fs::canonicalize(run_dir).with_context(|| format!("open {}", run_dir.display()))?;
    let manifest: Manifest = read_json(&run_dir.join("manifest.json"))?;
    ensure!(
        manifest.version == VERSION,
        "unsupported manifest version {}",
        manifest.version
    );
    // Tokens name staging directories and temporary images.
    ensure!(
        manifest.token.len() == 32 && manifest.token.bytes().all(|byte| byte.is_ascii_hexdigit()),
        "invalid session token in the manifest"
    );
    let layout = &manifest.layout;
    ensure!(
        fs::canonicalize(&layout.run_dir)? == run_dir,
        "the manifest belongs to {}",
        layout.run_dir.display()
    );
    let _lock = RunLock::acquire(&layout.lock())?;
    for path in manifest.endpoints.iter().chain(&manifest.overlays) {
        owned(path, &layout.run_dir)?;
    }
    for path in &manifest.pools {
        owned(path, &layout.pool_dir)?;
    }
    for path in &manifest.temporaries {
        ensure!(
            SessionLayout::is_temporary_image(path, &manifest.token),
            "invalid temporary image path {}",
            path.display()
        );
    }
    let owns_pool_dir = owns_pool_dir(layout, &manifest.token)?;
    let mut errors = Vec::new();
    for endpoint in &manifest.endpoints {
        errors.extend(Endpoint::adopt(endpoint.clone()).remove().err());
    }
    for file in manifest.overlays.iter().chain(&manifest.temporaries) {
        errors.extend(OwnedFile::adopt(file.clone()).remove().err());
    }
    // Once this session's pool directory is gone, another session may
    // publish one under the same name; its pools are left alone.
    if owns_pool_dir {
        for pool in &manifest.pools {
            errors.extend(OwnedFile::adopt(pool.clone()).remove().err());
            if let Some(parent) = pool.parent() {
                errors.extend(OwnedDir::adopt(parent.to_path_buf()).remove().err());
            }
        }
        if errors.is_empty() {
            errors.extend(remove_pool_dir(layout, &manifest.token).err());
        }
    } else {
        errors.extend(remove_staging(&layout.pool_staging(&manifest.token)).err());
    }
    if !errors.is_empty() {
        let messages = errors
            .iter()
            .map(|error| format!("{error:#}"))
            .collect::<Vec<_>>();
        bail!("cleanup failed: {}", messages.join("; "));
    }
    Ok(())
}

/// Returns whether the pool directory exists and belongs to session `token`.
///
/// A session publishes its pool directory only with the marker inside, so a
/// missing marker means that the directory is absent or has another owner.
fn owns_pool_dir(layout: &SessionLayout, token: &str) -> Result<bool> {
    let marker = layout.pool_marker();
    match fs::read_to_string(&marker) {
        Ok(owner) => Ok(owner == token),
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(false),
        Err(error) => Err(error).with_context(|| format!("read {}", marker.display())),
    }
}

/// Moves the pool directory of session `token` aside, then removes it.
///
/// The caller owns the directory and has removed its pools. The move frees
/// the name at once, and the staging name lets `cosim clean` finish the
/// removal after an interruption.
pub(crate) fn remove_pool_dir(layout: &SessionLayout, token: &str) -> Result<()> {
    let staging = layout.pool_staging(token);
    fs::rename(&layout.pool_dir, &staging)
        .with_context(|| format!("move {} aside", layout.pool_dir.display()))?;
    remove_staging(&staging)
}

/// Removes a staging directory, which holds at most the ownership marker.
fn remove_staging(staging: &Path) -> Result<()> {
    OwnedFile::adopt(SessionLayout::marker_in(staging)).remove()?;
    OwnedDir::adopt(staging.to_path_buf()).remove()
}

/// Accepts paths strictly below `root` whose existing parents stay inside it.
fn owned(path: &Path, root: &Path) -> Result<()> {
    let relative = path
        .strip_prefix(root)
        .with_context(|| format!("{} is outside {}", path.display(), root.display()))?;
    ensure!(
        !relative.as_os_str().is_empty()
            && relative
                .components()
                .all(|component| matches!(component, Component::Normal(_))),
        "invalid owned path {}",
        path.display()
    );
    let root = match fs::canonicalize(root) {
        Ok(root) => root,
        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(error).with_context(|| format!("resolve {}", root.display())),
    };
    let parent = path.parent().context("owned path has no parent")?;
    for ancestor in parent.ancestors() {
        if ancestor
            .try_exists()
            .with_context(|| format!("inspect {}", ancestor.display()))?
        {
            ensure!(
                fs::canonicalize(ancestor)?.starts_with(&root),
                "{} escapes {}",
                path.display(),
                root.display()
            );
            break;
        }
    }
    Ok(())
}

fn read_json<T: DeserializeOwned>(path: &Path) -> Result<T> {
    let text = fs::read(path).with_context(|| format!("read {}", path.display()))?;
    serde_json::from_slice(&text).with_context(|| format!("parse {}", path.display()))
}
