# SPDX-License-Identifier: Apache-2.0
"""Sphinx configuration for the cosim-gpu documentation site.

Documentation information architecture and visual theme are adapted from the
Zephyr Project documentation, with thanks to the Zephyr documentation
maintainers. This tribute is source-only; it is not rendered on the site.

The site is the only published form (GitHub Pages). Chinese is the primary
language and English is the synchronized translation. COSIM_DOCS_LANG selects
the source tree for a build; docs/scripts/build.sh builds zh and en and writes
a zh-first landing page.
"""

import os

DOCS_LANG = os.environ.get("COSIM_DOCS_LANG", "zh")
if DOCS_LANG not in ("zh", "en"):
    raise SystemExit(f"unsupported COSIM_DOCS_LANG={DOCS_LANG!r}")

project = "cosim-gpu"
author = "cosim-gpu contributors"
copyright = "2025-2026, cosim-gpu contributors"

language = "zh_CN" if DOCS_LANG == "zh" else "en"
root_doc = "index"
source_suffix = {".rst": "restructuredtext"}
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

extensions = [
    "sphinx_rtd_theme",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinxcontrib.mermaid",
    "sphinx.ext.githubpages",
]

# Zephyr-like reading experience: same theme as Zephyr's documentation.
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "logo_only": True,
    "navigation_depth": 4,
    "style_external_links": True,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
    "prev_next_buttons_location": "bottom",
}
html_title = "cosim-gpu 文档" if DOCS_LANG == "zh" else "cosim-gpu documentation"
html_logo = "_static/logo.svg"
html_static_path = ["_static"]
html_css_files = ["zephyr-condensed.css"]
html_js_files = ["language-switch.js"]
html_show_sourcelink = False
html_show_sphinx = False
html_last_updated_fmt = "%Y-%m-%d"

# GitHub Pages project site; override with COSIM_DOCS_BASEURL when the
# publishing repository or custom domain changes.
html_baseurl = os.environ.get(
    "COSIM_DOCS_BASEURL", "https://gevico.github.io/cosim-gpu/"
)
html_search_language = "zh" if DOCS_LANG == "zh" else "en"
mermaid_version = "12.1.0"
smartquotes = False
