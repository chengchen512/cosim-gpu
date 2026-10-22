# cosim-gpu documentation source

This directory contains the RST source of the cosim-gpu documentation site.
The built site is published to GitHub Pages; Chinese is the primary language
and English is a synchronized translation.

## Toolchain

- Sphinx 9.2 + native reStructuredText (no MyST), see requirements.txt
- sphinx_rtd_theme with an independent Apache-2.0 theme implementing the
  Zephyr-inspired visual design (`_static/zephyr-condensed.css`)
- sphinx-design, sphinx-copybutton, sphinxcontrib-mermaid

## Build and preview

~~~bash
python3 -m venv docs/.venv
docs/.venv/bin/pip install -r docs/requirements.txt
just docs          # strict build, both languages, zh-first landing
just docs-serve    # serve http://127.0.0.1:8010/
just docs-check    # bilingual parity + generated site verification
~~~

## Layout

~~~text
docs/
├── conf.py                 # shared configuration, COSIM_DOCS_LANG selects zh/en
├── requirements.txt        # pinned toolchain
├── _static/                # independent theme layer, logo, language switcher
├── scripts/                # build, serve, i18n check, site verification
├── zh/                     # primary Chinese source tree
├── en/                     # synchronized English mirror
├── NOTICE.md               # source-only attribution
└── README.md               # this file (not part of the built site)
~~~

## Writing rules

- Every page exists as a twin under docs/zh and docs/en with the same relative
  path (snake_case, .rst). Keep the heading skeleton identical.
- Chinese is written first; the English page is updated in the same change.
- No per-page first-line language link: the site language switcher handles it.
- Chapter index pages are navigation only (short intro + toctree); details go
  into child pages.
- Use :doc: / :ref: for cross references, code-block for commands, list-table
  for data tables, and keep heading depth to H2/H3.
- Support status (Supported/Experimental/Planned, support matrix) is deferred:
  do not add status claims or status columns.
- Attribution to Zephyr lives only in source files (this NOTICE, conf.py header
  and the theme CSS header), never on rendered pages. The theme is an
  independent Apache-2.0 implementation inspired by the Zephyr documentation;
  it contains no copied Zephyr CSS.
