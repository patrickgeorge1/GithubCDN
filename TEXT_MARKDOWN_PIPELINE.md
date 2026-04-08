# Text Markdown Pipeline (NT/OT)

## Purpose
This document explains how to generate chapter markdown (`.md`) files, update recipe text metadata (`hasText`), validate integrity, and keep app bundled assets aligned.

## Scope
- Repo: `GithubCDN`
- Data root: `BibleSpoken/data`
- Script: `scripts/generate_matei_markdown.py` (generalized for `NT` and `VT`)

## Backward Compatibility Guardrails (Required)
- Keep both recipe entry files during compatibility windows:
  - `BibleSpoken/data/recipe-not-cached.txt` (legacy app versions)
  - `BibleSpoken/data/recipe-not-cached-v2.txt` (newer app versions)
- Keep those two files equivalent unless a planned migration explicitly says otherwise.
- Do not change existing recipe step hashes for metadata-only updates.
- Keep both recipe delivery sources aligned (`jsdelivr` and custom CDN).

## What The Script Does
For one selected book:
1. Reads chapter `.mp3` files in the book folder.
2. Fetches chapter verses from `bibliaortodoxa.ro`.
3. Generates sibling `.md` files next to each `.mp3`.
4. Updates recipe path metadata for the matching book:
   - `BibleSpoken/data/recipe.txt`
   - `BibleSpoken/data/recipe-not-cached-v2.txt`
   - `BibleSpoken/data/bundled-recipe.txt` (only entries present there)
5. Writes a per-book JSON report.

## Required Arguments
- `--testament NT|VT`
- `--book-dir <book-folder>`
- `--book-index <index-from-filename-prefix>`
- optional `--report-path <json-report-path>`

Examples:
```bash
# NT example (Matei = NT01)
python3 scripts/generate_matei_markdown.py \
  --testament NT \
  --book-dir BibleSpoken/data/Noul-Testament/Matei \
  --book-index 1 \
  --report-path BibleSpoken/data/reports/01-Matei-text-report.json

# OT example (Facerea = VT01)
python3 scripts/generate_matei_markdown.py \
  --testament VT \
  --book-dir BibleSpoken/data/Vechiul-Testament/Facerea \
  --book-index 1 \
  --report-path BibleSpoken/data/reports/VT01-Facerea-text-report.json
```

## Batch Strategy
Use a wrapper loop/script that:
- iterates book directories,
- derives `NTxx`/`VTxx` index from filenames,
- runs the script per book,
- continues on failures,
- writes:
  - per-book reports under `BibleSpoken/data/reports/<batch-name>/`
  - one final batch summary report.

## Integrity Checks (Must Run)
After batch execution, verify:

1. File-pair integrity:
```bash
# Adapt testament folder as needed
python3 - <<'PY'
from pathlib import Path
root=Path("BibleSpoken/data/Vechiul-Testament")
mp3=list(root.rglob("*.mp3"))
md=list(root.rglob("*.md"))
missing=[p.with_suffix(".md") for p in mp3 if not p.with_suffix(".md").exists()]
print({"mp3":len(mp3),"md":len(md),"missingMdForMp3":len(missing)})
PY
```

2. Recipe metadata integrity:
```bash
python3 - <<'PY'
import json
from pathlib import Path
for f in [
  "BibleSpoken/data/recipe.txt",
  "BibleSpoken/data/recipe-not-cached-v2.txt",
  "BibleSpoken/data/bundled-recipe.txt",
]:
  d=json.loads(Path(f).read_text(encoding="utf-8"))
  total=0
  valid=0
  for s in d.get("steps",[]):
    for p in s.get("paths",[]):
      rp=p.get("referencePath","")
      if rp.endswith(".mp3"):
        total+=1
        pp=p.get("phonePath","")
        if p.get("hasText") is True:
          valid+=1
  print(f, {"totalMp3Entries": total, "validTextMetadata": valid})
PY
```

## Bundled App Sync (Important)
`GithubCDN` updates do not automatically update app bundled assets.

If bundled content is expected in the app (`BibleSpoken` repo), sync at least:
- `GithubCDN/BibleSpoken/data/bundled-recipe.txt`
  -> `BibleSpoken/assets/data/bundled-recipe.txt`
- any bundled markdown files required by that recipe
  -> `BibleSpoken/assets/data/...`

## Known Runtime Detail
Current app sync logic applies `PathMapping.referencePath` files only.  
`hasText` is recipe metadata and markdown path is derived from the matching audio path (`.mp3 -> .md`).

## Reports
Reports are generation artifacts for validation and troubleshooting.

Rule:
- Do not commit reports to `BibleSpoken/data/` in normal release flow.
- If reports are needed temporarily, keep them local or clean them before publish.
