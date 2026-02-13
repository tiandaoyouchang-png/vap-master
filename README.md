# vap-master

Unified CLI for generating VAP MP4s from a PNG sequence using VapTool 2.0.6.

## Files

- `vap_master.py`: CLI entrypoint.
- `VapBatch.java`: Headless VapTool runner (Java API).
- `VapBatch.class`: Precompiled runner (can be rebuilt).

## Prereqs

- Java 17 at `/Users/cqca202110203/.opencode/tools/java/temurin17/Contents/Home/bin/java`
- VapTool 2.0.6 at `/Users/cqca202110203/.opencode/tools/vaptool/tool2.0.6`
- System `ffmpeg` + `ffprobe` available in `PATH`

## Usage

Standard (VapTool default layout: RGB left, Alpha right, scale 0.5):

```bash
python3 "/Users/cqca202110203/.opencode/skills/vap-master/vap_master.py" \
  --input "/path/to/frames" \
  --output "/path/to/out.mp4" \
  --fps 25 \
  --mode standard
```

Mask-left (post-process to: Mask/Alpha left, RGB right; 1008x1334 each; total 2016x1334):

```bash
python3 "/Users/cqca202110203/.opencode/skills/vap-master/vap_master.py" \
  --input "/path/to/frames" \
  --output "/path/to/out.mp4" \
  --fps 25 \
  --mode mask-left
```

Notes:

- Input frames must be PNGs with numeric suffixes (e.g. `name_00001.png`).
- Frames are normalized to `1008x1334` (a `1344` height is cropped to `1334`).
- `mask-left` mode re-encodes once with ffmpeg to swap regions, then updates the embedded `vapc` atom via `mp4edit`.

## Rebuild VapBatch.class (optional)

```bash
JAVAC="/Users/cqca202110203/.opencode/tools/java/temurin17/Contents/Home/bin/javac"
ANIMTOOL="/Users/cqca202110203/.opencode/tools/vaptool/tool2.0.6/animtool.jar"
cd "/Users/cqca202110203/.opencode/skills/vap-master" && "$JAVAC" -cp "$ANIMTOOL" VapBatch.java
```
