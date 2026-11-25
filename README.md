# The World in One Day — Tuesday 24 November 2026

[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/top234/news-image-20261124-entry-v2/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![leaderboard](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)

One page of world news: **38 stories, 9 regions, 21 fields** — every one dated
Tuesday 24 November 2026. Thirteen pictured stories (numbered 1–13) with a
vector scene drawn for each, a 25-item "Also on Tuesday 24 November" list
(14–38), a UTC timeline, a numbers strip, a dotted world map with numbered
pins, a date check, and a source footer.

## Render

```sh
python3 generate.py        # writes entry.png (1024x1024, deterministic)
node main.ts               # same, via OUTPUT_DIR; falls back to bundled entry.png
```

`generate.py` uses Python + PIL only, reads no clock, network, or random
source: two runs produce byte-identical PNGs. All 38 stories come from the
verified facts in `../FACTS.md` — nothing else was added.

## Files

- `generate.py` — draws `entry.png` from the verified facts
- `main.ts` — entrypoint: runs `generate.py`, verifies the PNG
  (signature, IHDR 1024×1024, ≤ 1 MiB, sha256), falls back to the bundled PNG
- `entry.png` — the rendered page (bundled fallback)
- `package.json` — `render` / `start` scripts
