# SACCADE

**Browser-native image text extraction. Zero external dependencies. Xinu compliant.**

During a saccade, the eye is blind. Saccade only sees what it lands on.

---

## What it is

Saccade is a single-file OCR tool that runs entirely in the browser. No server. No cloud. No API calls. Drop an image, label some character clusters, and get text out.

It works on any modern browser. It works offline. It works on your phone.

## How it works

```
INGEST → THRESH → SEGMENT → ATLAS → CLUSTER → LABEL → WARM UP → QUANTIZE → MATCH → EMIT
```

**SEGMENT** finds connected ink blobs using union-find flood fill, then runs a dot/tail merge pass to reconnect `i`, `j`, `!`, `?` and citation superscripts.

**CLUSTER** groups visually similar blobs by cosine distance on 48×48 pixel representations. Hull fill ratio filtering removes bracket fragments and corner noise. Up to 40 clusters per image, sorted by population.

**LABEL** shows each cluster at native blob resolution. You type the character. All 40 clusters are shown — auto-match suggestions pre-fill the input box in amber; you confirm, correct, or skip. Large clusters (>50 blobs) show a warning in case they contain mixed characters. DONE is always available with no minimum label requirement.

**WARM UP** trains a two-layer neural net (`2304→64→95`) on balanced library samples. Cross-entropy loss, cosine LR decay, 45 epochs. Gradient clipping prevents divergence. If direct labels cover ≥20% of image blobs, WARM UP is skipped entirely — label-only mode uses your labels directly with no net inference.

**QUANTIZE** converts trained float32 weights to ternary `{-1,0,+1}` via BitNet b1.58 absmean thresholding, then precomputes TMAC lookup tables (3⁴=81 patterns per 4-weight chunk). Skipped in label-only mode.

**MATCH** maps each blob to a character. Blobs from directly-labeled clusters (≤60 members) use the label verbatim — no inference, no margin check, no uncertainty. Larger unlabeled clusters go through the net. Uncertain net outputs (margin < 0.12) emit blank rather than guess wrong.

**GAP FILL** (after LABEL) — chars with zero library coverage get a reference render + best-candidate blob from the image. Confirm or mark "not in image." Builds coverage organically session by session.

## The library

Every session builds your `.sacat` atlas file — labeled blob samples stored with font fingerprints. Export it, import it anywhere. The library auto-matches previously seen clusters so LABEL gets shorter every run. A **CLEAR LIB** button wipes library and localStorage and invalidates the net cache.

**EXPORT DEBUG** downloads a timestamped `.txt` with all four debug panels: BLOBS (per-blob output, source, margin, top-1/top-2), CLUSTERS (index, label, blob count), TRAINING (samples per char, capped vs raw), LIBRARY (full breakdown).

```
📚 Library: 37 chars · 965 samples
```

## Usage

1. Open `Saccade.html` in any modern browser — local file or from GitHub Pages
2. Drop or select an image
3. Label character clusters — amber suggestions pre-fill, confirm or correct each one
4. If library coverage is good, WARM UP skips automatically (label-only mode)
5. Copy the extracted text
6. Export your `.sacat` to keep labels for next time

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
- **Label-only mode** — direct label short-circuit bypasses net entirely when coverage is sufficient

No external libraries. No pre-trained weights.

## Changelog

### v45 (current)
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
