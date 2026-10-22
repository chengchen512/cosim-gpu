.. SPDX-License-Identifier: Apache-2.0

.. _contrib-documentation:

Documentation rules
===================

This page defines the source format, the bilingual rules, the page templates and
formatting conventions, and the build and check commands. Read it before
changing any page under ``docs/``.

Source format and toolchain
---------------------------

- Documentation sources are reStructuredText (``.rst``) under ``docs/``; the
  project does not use MyST or Markdown.
- The site is built with Sphinx and the ``sphinx_rtd_theme`` theme, with the
  ``sphinx-design``, ``sphinx-copybutton`` and ``sphinxcontrib-mermaid``
  extensions; see ``docs/conf.py``.
- The built site (GitHub Pages) is the only published form; ``docs/README.md`` and
  ``docs/NOTICE.md`` are not site pages.
- Chinese is the primary language (``docs/zh/``); English is the synchronized
  mirror (``docs/en/``).

Chinese primary and English mirror
----------------------------------

- Every page has a file under both ``docs/zh/`` and ``docs/en/``, with the same
  relative path, a snake_case file name and the ``.rst`` extension.
- Write the Chinese page first and update the English page in the same change; never
  change only one language.
- Do not add a language link on the first line. The site language switcher handles
  it, and rendered pages contain no first-line link to the other language version.
- The heading-level skeleton must match: the same number of H2 and H3 sections in
  the same order. ``docs/scripts/check_i18n.py`` compares the heading-level
  sequence of each page pair.
- After changing documentation, run ``just docs-check``, which builds both
  languages and runs the bilingual and site checks.

Chapter index template
----------------------

Chapter index pages are navigation only: one sentence on what the chapter
answers, then the toctree and a recommended path. Keep an index page under 80
lines; details belong in child pages.

.. code-block:: rst

   .. _chapter-index:

   Chapter title
   =============

   One sentence on the question this chapter answers and who it is for.

   In this chapter
   ---------------

   .. toctree::
      :maxdepth: 1

      page_one
      page_two

   Recommended path
   ----------------

   - New to the topic: start with page_one
   - Looking up a fact: go to page_two

Headings and page structure
---------------------------

- Each page has exactly one H1 whose title matches the navigation entry.
- Use H2 for sections and H3 only when needed; do not use H4 or deeper headings.
- Declare an explicit label at the top of every page, for example
  ``.. _contrib-workflow:``, for cross-page references.
- End every page with a "Related pages" section containing three to six
  ``:doc:`` or ``:ref:`` links.
- Keep the heading-level skeleton identical between the Chinese and English pages.

RST conventions
---------------

- Use ``.. code-block:: bash`` (or the matching language) for commands; do not
  put a shell prompt inside a code block, so commands can be copied directly.
- Prefer ``.. list-table::`` with ``:header-rows: 1`` for data tables, at most
  six columns; use ``grid-table`` only when cells need multiple paragraphs.
- Use only ``note``, ``tip`` and ``warning`` admonitions; do not add custom
  styles.
- Use double backticks for inline literals, for example ``just docs-check``.
- Link within a chapter with ``:doc:``; reference other chapters only with
  ``:ref:`` and an existing label.
- Use the ``.. mermaid::`` directive for architecture diagrams.
- Keep file names in snake_case, use ``index.rst`` for chapter indexes, and do
  not translate file names.
- Use semantic line breaks: one complete semantic unit per line makes reviews and
  diffs easier.

Cross references and labels
---------------------------

- Name labels ``.. _<chapter>-<page>:``, for example ``.. _contrib-ci:``, and
  avoid renaming a published label.
- Link within a chapter with the relative ``:doc:`` role, for example
  ``workflow``; link across chapters with ``:ref:`` plus an existing label,
  such as ``gs-index``.
- Maintain each fact on one canonical page and link to it instead of copying whole
  sections.
- The build treats unresolved references and duplicate labels as errors, so confirm
  that a label exists before referencing it.

Support status (deferred)
-------------------------

Support status (Supported, Experimental, Planned, status columns or a support
matrix) is deferred: this round of documentation adds no status claims, status
columns or badges. Pages describe capabilities that exist, for example "the
example uses the single-gpu machine", without judging whether a capability is
supported.

Build and checks
----------------

Install the toolchain once:

.. code-block:: bash

   python3 -m venv docs/.venv
   docs/.venv/bin/pip install -r docs/requirements.txt

Then use these commands:

.. code-block:: bash

   just docs          # strict build of both languages (warnings are errors)
   just docs-serve    # build and preview at http://127.0.0.1:8010/
   just docs-check    # build + bilingual check + generated-site check

``just docs-check`` runs ``docs/scripts/build.sh``,
``docs/scripts/check_i18n.py`` and ``docs/scripts/verify_build.py`` in order:

- Bilingual check: every page has a twin in the other language, every page has an
  explicit label, the heading-level skeleton matches, and no first-line language
  link exists.
- Site check: the landing page exists and redirects to the Chinese site, every
  source file produced an HTML page, the page count meets the expectation, no migration stub marker remains, and the
  theme and language switcher are loaded.

``.github/workflows/docs.yml`` runs the same build and checks when
``docs/**`` changes; builds from ``main`` are published to GitHub Pages.

Related pages
-------------

- :doc:`workflow`
- :doc:`rust_guidelines`
- :ref:`index`
