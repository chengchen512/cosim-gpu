// SPDX-License-Identifier: Apache-2.0

//! Byte quantities parsed from integers or binary-unit strings.

use std::borrow::Cow;
use std::fmt;

use anyhow::{Context, Result, ensure};
use schemars::{JsonSchema, Schema, SchemaGenerator};
use serde::{Deserialize, Serialize};

/// A positive byte count that also fits in a file offset.
///
/// YAML accepts an integer number of bytes or a string such as `16G`;
/// units are binary multiples.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(try_from = "SizeInput", into = "u64")]
pub struct ByteSize(u64);

impl ByteSize {
    /// Default alignment of memory-pool regions.
    pub(crate) const TWO_MEBIBYTES: Self = Self(2 * 1024 * 1024);

    /// Returns the number of bytes.
    pub fn bytes(self) -> u64 {
        self.0
    }

    /// Returns whether the size is a power of two.
    pub fn is_power_of_two(self) -> bool {
        self.0.is_power_of_two()
    }
}

impl TryFrom<u64> for ByteSize {
    type Error = anyhow::Error;

    fn try_from(bytes: u64) -> Result<Self> {
        ensure!(
            bytes > 0 && bytes <= i64::MAX as u64,
            "byte size out of range: {bytes}"
        );
        Ok(Self(bytes))
    }
}

impl From<ByteSize> for u64 {
    fn from(size: ByteSize) -> Self {
        size.0
    }
}

impl fmt::Display for ByteSize {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}", self.0)
    }
}

impl JsonSchema for ByteSize {
    fn schema_name() -> Cow<'static, str> {
        "ByteSize".into()
    }

    fn json_schema(generator: &mut SchemaGenerator) -> Schema {
        SizeInput::json_schema(generator)
    }
}

#[derive(Deserialize, JsonSchema)]
#[serde(untagged)]
enum SizeInput {
    Bytes(u64),
    Text(String),
}

impl TryFrom<SizeInput> for ByteSize {
    type Error = anyhow::Error;

    fn try_from(input: SizeInput) -> Result<Self> {
        let bytes = match input {
            SizeInput::Bytes(bytes) => bytes,
            SizeInput::Text(text) => parse_size::Config::new()
                .with_binary()
                .parse_size(&text)
                .with_context(|| format!("invalid byte size {text:?}"))?,
        };
        Self::try_from(bytes)
    }
}
