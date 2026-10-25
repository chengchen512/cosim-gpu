<!--
SPDX-License-Identifier: Apache-2.0
-->

# README animation assets

These silent, looping GIFs are excerpts from the locally produced film
`Cosim-GPU_开箱即用的AI-Infra学习环境.mp4` (390 seconds, 1920 × 1080,
60 fps). The source file is in `cosim-gpu-film/video/out/` in the film project.
Both language versions of the project README use the same assets.
The GIF assets in this directory use the project's [Apache 2.0 license](../../../LICENSE).

| Asset | Source interval | Crop: width × height, x, y | Output |
| --- | --- | --- | --- |
| `single-node-multi-gpu.gif` | 03:52.200–04:02.000 | 900 × 720, 880, 160 | 560 × 448, 9.8 s |
| `multi-node-multi-gpu.gif` | 04:02.400–04:10.800 | 900 × 720, 880, 160 | 560 × 448, 8.4 s |
| `qemu-gem5-shared-memory.gif` | 01:52.400–02:04.400 | 1920 × 860, 0, 0 | 864 × 387, 12 s |

All three excerpts retain the source playback speed and use 10 fps. Topology
crops focus on the QEMU processes, MI300X models and per-machine memory pools.
The multi-node excerpt shows four independent machines in a local session.
The communication excerpt includes vfio-user messages, the shared pool
mappings and animated data transfers.

## Encoding

Extract each interval with FFmpeg, then apply its crop and a Lanczos resize.
Use this filter after resizing to generate and apply a 64-color palette:

~~~text
split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle
~~~

Set `-loop 0` for continuous playback and optimize the encoded GIF with
`gifsicle -O3 --lossy=120`. Each GIF frame lasts 100 ms.
Check the decoded frames, duration, crop boundaries and
README image links after regenerating the assets.
