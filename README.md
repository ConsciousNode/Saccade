# SACCADE

**Browser-native image text extraction. Zero external dependencies. Xinu compliant.**

During a saccade, the eye is blind. Saccade only sees what it lands on.

---

## What it is

Saccade is a single-file OCR tool that runs entirely in the browser. No server. No cloud. No API calls. Drop an image and get text out: Saccade teaches itself to read from the fonts your browser already has. For unusual fonts you can label glyph clusters too, and your labels build a library that carries over between sessions.

It works on any modern browser. It works offline. It works on your phone.

## How it works

```
INGEST → THRESH → SEGMENT → ATLAS → CLUSTER → (LABEL) → WARM UP → QUANTIZE → MATCH → EMIT
```

**THRESH** binarises with an adaptive threshold (integral image), auto-detecting dark backgrounds. Small text (median blob under ~12 px) is upscaled with smoothing and binarised again, but only if that separates more letters.

**SEGMENT** finds 8-connected ink blobs, then runs a dot merge pass to reconnect `i`, `j`, `!` and `?` (a dot must sit close to, and centred on, its body).

**CLUSTER** groups visually similar blobs by cosine distance on 48×48 pixel representations, for the optional labeling step.

**LABEL** (optional, the **LABEL** button) shows each cluster at native resolution so you can type the character. Auto-match suggestions pre-fill from your library, and a GAP FILL step offers characters the library doesn't cover yet. Off by default: you don't need it for ordinary fonts.

**WARM UP** trains a two-layer net (`2304→64→95`) on every printable character rendered in three font families (sans, serif, mono), regular and bold, with stroke-weight and threshold variations, cropped tight to the ink exactly like real blobs. Your library samples, if any, are added on top. About 20–30 s the first time; the net is cached per text size, in the session and in the browser, so the next visit starts at once.

**QUANTIZE** converts the trained float32 weights to ternary `{-1,0,+1}` via BitNet b1.58 absmean thresholding, then precomputes TMAC lookup tables (3⁴=81 patterns per 4-weight chunk).

**MATCH** reads each blob with the net, then lets the blob's geometry rule out what it can't be:
- **Size and position on the line.** x-height letters, tall letters and capitals, and descenders (`g p q y`) are told apart by where the blob sits against the line's baseline and cap height. That is how `o/O`, `s/S` and `v/V` get their case back (every blob is stretched to the same square, which erases it). Small marks are read by height alone: `. ,` on the baseline, `-` in the middle, `' "` at the top, `_` below.
- **Aspect gate.** A blob can only be a character that some font renders about that narrow or wide. This splits `P/R/F`, and keeps a thin `l` from being read as `T`.
- **Dots.** A blob with a merged dot is `i j ! ?`; one without never is. `: ; " = %` are never one blob.
- **Words.** A digit inside a word of letters becomes the net's best letter, and the other way round. `l` and `I` are chosen by the word's case.

Blobs from labeled clusters use your label directly. Uncertain blobs emit nothing rather than guess.

**EMIT** assembles lines from full-size blobs (small marks join the line that covers them) and finds word gaps by splitting the page's gap sizes into two groups. That works for proportional and monospaced text alike.

## How well it reads

`python3 tests/saccade-read.py` renders four lines of text (pangrams, digits, punctuation) in each case below, drops each image into the page and scores the output with no labeling at all:

| Text | Characters correct |
|---|---|
| sans-serif 32 px | 98.7% |
| sans-serif 24 px | 96.7% |
| monospace 24 px | 96.0% |
| serif 24 px | 95.3% |
| sans-serif 24 px, light on dark | 93.3% |
| sans-serif 16 px | 92.7% |
| sans-serif 12 px | 88.0% |
| serif 16 px | 82.0% |

v45 scored 0% on all of these without labeling, since it could only read characters you had labeled.

**Known limits.**
- Letters that touch become one blob, and come out wrong or blank. This hits ligatures like `ffl` (in every test) and small serif text the most. A cut-at-the-thinnest-column splitter was tried, and hurt more than it helped.
- Fonts unlike sans, serif and mono (script, decorative, handwriting) need labeling.
- These are clean renders: photos of paper and heavy JPEG haven't been measured yet.

## The library

Every session builds your `.sacat` atlas file — labeled blob samples stored with font fingerprints. Export it, import it anywhere. The library auto-matches previously seen clusters so LABEL gets shorter every run. A **CLEAR LIB** button wipes library and localStorage and invalidates the net cache.

**EXPORT DEBUG** downloads a timestamped `.txt` with all four debug panels: BLOBS (per-blob output, source, margin, top-1/top-2), CLUSTERS (index, label, blob count), TRAINING (samples per char, capped vs raw), LIBRARY (full breakdown).

```
📚 Library: 37 chars · 965 samples
```

## Usage

1. Open `Saccade.html` in any modern browser — local file or from GitHub Pages
2. Drop or select an image
3. Wait for WARM UP the first time (about 20–30 s; after that the net is saved and reused)
4. Copy the extracted text
5. For an unusual font, turn **LABEL** on and label the clusters (amber suggestions pre-fill); export your `.sacat` to keep the labels

## Philosophy

- **Single file.** The entire tool is `Saccade.html`. No build step. No dependencies.
- **Xinu compliant.** Browser as bare metal. The only runtime is what ships with the browser.
- **Offline first.** Nothing leaves your device.
- **Browser agnostic.** Any modern engine. Tested on Android Chrome and desktop Chromium.
- **Responsive.** Works on mobile and desktop without reformatting.
- **Honest.** Uncertain output is blank, not wrong.

## Technical lineage

Built on ConsciousNode's in-house neural stack:

- **TinyNet** — two-layer classifier (2304→64→95), cross-entropy loss, cosine LR decay
- **TMAC** — ternary matrix multiplication via lookup tables, derived from BitNet b1.58
- **Adaptive threshold** — integral image binarization with dark-background auto-detection
- **Union-find segmentation** — connected component labeling with dot/tail merge
- **Greedy nearest-neighbor clustering** — cosine similarity at 48×48, hull fill filter
- **Self-taught from fonts** — synthetic glyphs in three families, cropped like real blobs, plus geometry rules at match time

No external libraries. No pre-trained weights.

## Changelog

### v46 — 2026-10-29 · Kham + Kehai Interim
- **Self-teaching works, and is the default.** Two bugs had sunk it since v2:
  - Synthetic training glyphs were the whole render canvas while real blobs are cropped tight, so the net learned pictures it never saw.
  - The learning rate was ~10× too high for 2,304 inputs, and training collapsed to a single class.

  Both are fixed, with three font families and a no-labels-needed WARM UP. Labeling is now optional (LABEL button).
- **Geometry rules in MATCH:** case from position on the line, small-mark rules, an aspect gate (the P/R/F split from the handoff, generalised), dot rules, and word context for letters vs digits and l/I.
- **Segmentation:**
  - 8-connected blobs; thin glyphs (`l I |`), dashes, underscores and i-dots are no longer filtered out.
  - The dot merge no longer jumps a full stop onto the next line.
  - Line grouping is no longer split by apostrophes and commas.
  - Word gaps work for monospace.
- **Thresholding:** colour correction snaps flat patches to the background level, not pure black or white (the 8-px speck grid on dark images). Small text is upscaled when that helps.
- **Speed:** sparse first-layer training (same SGD, several times faster). Training is seeded (same image → same text). The net is saved in localStorage.
- Label-only mode (skipping WARM UP when labels covered ≥20% of blobs) is gone: the net now always runs for unlabeled blobs, which used to come out blank. It's cached, so this costs nothing after the first run.
- `tests/saccade-read.py` reads rendered test images through the real page and scores them.
- The WASM kernel is unchanged: it still boots but isn't used by the OCR (moving segmentation into it is still on the handoff list).


### v45
- **DIRECT_MAX raised 30→60** — `t`(53)/`r`(41)/`n`(41)/`h`(33) were labeled and clean but excluded from direct path by old limit; now 52% of blobs covered directly, reliably triggering label-only mode
- **Label-only threshold lowered to 20%** — extra headroom for images with different blob distributions

### v44
- **Label-only threshold lowered 50%→30%** — cluster 0 (206 blobs) excluded by DIRECT_MAX was eating ~30% of coverage, pushing below 50% threshold so net kept running

### v43
- **Label-only mode** — if direct labels cover ≥threshold of image blobs, WARM UP and QUANTIZE skip entirely; output comes purely from user labels; pipeline shows coverage % in WARM UP stage

### v42
- **NaN explosion fixed** — oversampling to majority class size caused gradient explosion; now oversamples to fixed TARGET_SAMPLES=15 per char
- **Gradient clipping** — CLIP=5.0 in LinearLayer.step() prevents weight updates from exploding
- **NaN detection** — if weights contain NaN after training, warmUpWithLib returns null gracefully

### v41
- **Large cluster direct-label bypass** — clusters >30 blobs skip direct path; net infers each blob individually so mixed vowel clusters get properly distinguished
- **Training panel** — now shows capped training count alongside raw library count

### v40
- **ATLAS stage now lights up** — was never calling setStage('atlas',...); fixed
- **EXPORT DEBUG button** — one click downloads timestamped .txt with all four debug panels

### v39
- **Inverse frequency weighting removed** — per-sample LR scaling destabilized SGD; replaced with balanced oversampling
- **Balanced oversampling** — minority classes oversampled to match majority (capped at MAX_ENTRIES=25)
- **Threshold reverted 0.72→0.78** — lower threshold was causing ligature merging (fi, ft)

### v38
- **Inverse frequency weight cap lowered 8×→3×** — v37 cap caused `y` to flood inference
- **Cluster threshold lowered 0.78→0.72** — better splits e/o and P/F/R (later reverted)
- **Mixed cluster warning** — large clusters show "skip if mixed chars!"

### v37
- **Class imbalance fixed** — training now caps at 20 entries per char; inverse frequency weighting boosts rare chars up to 8× (later revised)
- **Large cluster warning** — label modal shows ⚠ N blobs when cluster has >50 members

### v36
- **Debug panel crash fixed** — panels wrapped in try/catch so any rendering error never kills the pipeline
- **Spread guard in lineToString** — explicit field copy replaces `{...d}` spread
- **emit-done stage** fires after debug panels complete

### v35
- **Debug drawer** — toggle with DEBUG button; four tabs: BLOBS, CLUSTERS, TRAINING, LIBRARY
- `matchBlobDebug` variant returns full confidence record
- `--green` and `--red` CSS variables added to theme

### v34
- **fontFP gate removed from training** — was silently dropping vowels labeled at slightly different medH
- **Margin threshold raised 0.08→0.12** — net blanks uncertain matches rather than guessing wrong chars

### v33
- **TextDetector removed** — Saccade always uses its own pipeline; fully browser-agnostic as intended
- **WARM UP progress span fixed** — dedicated `#warm-pct` element, no more re-creation on every tick
- **`labeledSamples` parameter removed** from warmUpWithLib

### v32
- **Library freeze fixed** — autoMatch suggestions now computed lazily one cluster at a time with tick() yield; 10-20× faster lookups via normalized dot products
- **sacatFromJSON** and **addToLib** store normalized `scaled` copy alongside raw pixels

### v31
- **Gap fill threshold raised 0.30→0.50** — only shows chars where image actually has a plausible match
- **Gap fill filters to plausible matches only**
- **`autocapitalize="none"`** on both label and gap fill inputs

### v30
- **All clusters shown during LABEL** — no hidden auto-matches; every cluster displayed with suggestion pre-filled
- **DONE always available** — no minimum label count
- **Gap fill phase** — chars with zero library coverage get reference render + best-match blob
- **Synth removed** — training data is 100% real labeled blobs
- **Cluster threshold lowered 0.85→0.78**
- **Tab key skips cluster**

### v29
- **Label modal hang fixed** — `MIN_CONFIRM_FLOOR=5` prevents stale library from eating all clusters
- **Pipeline freeze fixed** — `finish()` resolves Promise when clusters exhausted
- **Labeling affects output** — labeled clusters short-circuit net inference at MATCH time
- **CLEAR LIB button**
- **Net cache invalidation fixed** — `_trainedLibCount` tracks library size
- **Responsive layout** — `100dvh`, vertical stack on ≤600px, flex-wrap bars

### v28
- Fixed `.sacat` import: `fontFP` preserved through export/import round-trip
- Confidence margin lowered 0.15→0.08
- Epochs bumped 35→45

### v20–v27
- v27: Cluster previews at native blob resolution
- v26: 48×48 input resolution, TMAC ternary inference, QUANTIZE stage
- v25: Minimum 20 labels, max clusters 40, hull fill filter
- v24: Library cap 20 per char, confidence margin gate
- v23: Cluster threshold 0.85, ink density filter 5%
- v22: Font fingerprinting, `.sacat` MIME type fix
- v21: Training 4-5min→~90s, dot/tail merge, PROSE_PRIOR removed
- v20: `.sacat` library, CLUSTER stage, LABEL UI, WARM UP on library

### v19
- Neural classifier replaces profile-based matcher
- TinyNet: 1024→128→95, trained on synthetic data
- WARM UP stage added

### v12–v18
- Profile-based matching engine iterations
- WAT kernel integration (standby)
- Preprocessing pipeline established

---

*ConsciousNode SoftWorks — Greenwood, South Carolina*
*Built by Kham and Vael Interim*
