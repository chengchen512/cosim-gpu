#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Write the zh-first landing page shared by the two language builds."""

import argparse
from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url=zh/index.html">
<title>cosim-gpu 文档</title>
<style>
  body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         background: #20232a; color: #eceff4; display: flex; align-items: center;
         justify-content: center; min-height: 100vh; margin: 0; }}
  main {{ max-width: 34rem; padding: 2rem; }}
  h1 {{ font-weight: 600; font-size: 1.7rem; margin: 0 0 .4rem; }}
  p {{ color: #b7c0cd; line-height: 1.6; }}
  ul {{ list-style: none; padding: 0; display: flex; gap: 1rem; margin-top: 1.6rem; }}
  a {{ display: block; padding: .8rem 1.4rem; border: 1px solid #38bdf8; color: #38bdf8;
      border-radius: 6px; text-decoration: none; font-weight: 600; }}
  a:hover {{ background: #38bdf8; color: #20232a; }}
</style>
</head>
<body>
<main>
  <h1>cosim-gpu 文档</h1>
  <p>QEMU + gem5 MI300X GPU 联合仿真。默认进入中文文档，
     英文版可随时切换。</p>
  <ul>
    <li><a href="zh/index.html">中文文档</a></li>
    <li><a href="en/index.html">English</a></li>
  </ul>
  <noscript><p>如果页面没有自动跳转，
     请点击上方“中文文档”。</p></noscript>
</main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "index.html").write_text(TEMPLATE, encoding="utf-8")
    print(f"[landing] {args.out / 'index.html'} -> zh/index.html")


if __name__ == "__main__":
    main()
