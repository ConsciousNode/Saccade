# SACCADE

**Browser-native image text extraction. Zero external dependencies. Xinu compliant.**

During a saccade, the eye is blind. Saccade only sees what it lands on.

---

## What it is

Saccade is a single-file OCR tool that runs entirely in the browser. No server. No cloud. No API calls. Drop an image, label some character clusters, watch the neural net warm up — and get text out.

It works on any modern browser. It works offline. It works on your phone.

## How it works

```
INGEST → THRESH → SEGMENT → ATLAS → CLUSTER → LABEL → WARM UP → QUANTIZE → MATCH → EMIT
```

**SEGMENT** finds connected ink blobs in the binarized image using a union-find flood fill, then runs a dot/tail merge pass to reconnect `i`, `j`, `!`, `?` and citation superscripts before clustering.

**CLUSTER** groups visually similar blobs by cosine distance on 48×48 pixel representations. Hull fill ratio filtering removes bracket fragments and corner noise before clustering. Up to 40 clusters per image, sorted by population.

**LABEL** shows each cluster at native blob resolution — six example blobs, rendered crisp. You type the character. At least 5 clusters always shown even if the library auto-matches everything, so stale library state can't silently eat the session. Minimum label count adapts to how many clusters are actually present.

**WARM UP** trains a two-layer neural net (`2304→64→95`) on labeled samples plus synthetic augmentation. Cross-entropy loss, cosine LR decay, 45 epochs. Progress shown live in the pipeline strip. Cached net invalidates if the library has changed size since last training.

**QUANTIZE** converts trained float32 L1 weights to ternary `{-1,0,+1}` via BitNet b1.58 absmean thresholding, then precomputes TMAC lookup tables (3⁴=81 patterns per 4-weight chunk). Inference at 48×48 costs the same as float32 at 32×32.

**MATCH** runs each blob through the quantized net. Blobs whose cluster was directly labeled during this session short-circuit inference entirely — the label is used verbatim. All other blobs go through the net; those where the margin between top-1 and top-2 probability is below 0.08 are skipped (uncertainty is honest silence, not wrong output).

## The library

Every session builds your `.sacat` atlas file — a JSON archive of labeled blob samples, font-fingerprinted to prevent cross-font contamination. Export it, import it anywhere. The library auto-matches previously labeled clusters so the LABEL stage gets shorter with every run. A **CLEAR LIB** button is available if the library gets contaminated or you want a fresh start.

```
📚 Library: 30 chars · 579 samples
```

## Usage

1. Open `Saccade.html` in any modern browser
2. Drop or select an image
3. Label character clusters (at least a few — the rest auto-match from your library)
4. Wait for WARM UP and QUANTIZE (~90 seconds on mobile)
5. Copy the extracted text
6. Export your `.sacat` library to keep labels for next time

## Philosophy

- **Single file.** The entire tool is `Saccade.html`. No build step. No dependencies.
- **Xinu compliant.** Browser as bare metal. The only runtime is what ships with the browser.
- **Offline first.** Nothing leaves your device.
- **Browser agnostic.** Any modern engine. Tested on Android Chrome.
- **Responsive.** Works on mobile and desktop without reformatting.

## Technical lineage

Built on ConsciousNode's in-house neural stack:

- **TinyNet** — two-layer classifier pulled from Simulacra's LinearLayer architecture
- **TMAC** — ternary matrix multiplication via lookup tables, derived from BitNet b1.58 and FPSS
- **Adaptive threshold** — integral image binarization with dark-background auto-detection
- **Union-find segmentation** — connected component labeling with dot/tail merge
- **Greedy nearest-neighbor clustering** — cosine similarity at 48×48, hull fill filter

No external libraries. No pre-trained weights.

## Changelog

### v41 (current)
- **Large cluster direct-label bypass** — clusters with >30 blobs are no longer short-circuited via blobLabels; net infers each blob individually so mixed vowel clusters (e/o/a/i/u) get properly distinguished instead of all becoming one label
- **Training panel fixed** — now shows capped training count (what net actually saw) alongside raw library count, so 314 lib samples for e correctly shows as 25 training samples
- **DIRECT_MAX=30** — clean threshold: small clusters (single char, clear label) use direct path; large mixed clusters go through net

### v40
- **ATLAS stage now lights up** — was never calling setStage('atlas',...); now fires between CLUSTER and LABEL
- **EXPORT DEBUG button** — one click downloads a timestamped .txt with all four debug panels (BLOBS, CLUSTERS, TRAINING, LIBRARY); no more copy-pasting

### v39
- **Inverse frequency weighting removed** — per-sample LR scaling destabilized SGD, causing net to collapse to K/S output; replaced with balanced oversampling
- **Balanced oversampling** — minority classes oversampled to match majority class size (capped at MAX_ENTRIES=25); cleaner than weighted loss for small datasets
- **Threshold reverted 0.72→0.78** — lower threshold was causing ligature merging (fi, ft clusters) and over-fragmentation; 0.78 was correct

### v38
- **Inverse frequency weight cap lowered 8×→3×** — v37's 8× cap was causing `y` (28 samples) to get boosted so hard it flooded inference; now capped at 3× for gentler balancing
- **Cluster threshold lowered 0.78→0.72** — better splits e/o and P/F/R which were still merging
- **Mixed cluster warning** — large clusters (>50 blobs) now say "skip if mixed chars!" so you know to skip e/o mixed clusters rather than labeling them as one char
- **MAX_ENTRIES raised 20→25** — gives net slightly more data per char for chars with many real samples

### v37
- **Class imbalance fixed** — training now caps at 20 entries per char (not samples×weight), so `t`=71 and `o`=4 get equal representation; previously `t`/`n`/`h` were drowning everything else causing margin 0.00 on all net inferences
- **Inverse frequency weighting** — rare chars get proportionally higher effective LR (up to 8×) during training; forces net to learn boundaries for low-sample chars
- **Large cluster warning** — label modal shows ⚠ N blobs when a cluster has >50 members so you don't accidentally skip the most important cluster

### v36
- **Debug panel crash fixed** — panels wrapped in try/catch so any rendering error never kills the pipeline or blanks output
- **Spread guard in lineToString** — explicit field copy replaces `{...d}` spread to prevent unexpected throw
- **emit-done stage** now fires after debug panels complete, so green dot accurately reflects full completion

### v35
- **Debug drawer added** — toggle with DEBUG button in output bar; four tabs:
  - **BLOBS** — per-blob table: position, output char, source (direct/net/blank), margin, top-1, top-2
  - **CLUSTERS** — cluster index, label, blob count, sample count
  - **TRAINING** — samples per char used in training; zero-coverage chars highlighted red
  - **LIBRARY** — full library breakdown sorted by sample count, fingerprinted sample count per char
- `matchBlobDebug` variant returns full confidence record without duplicating matchBlob logic
- `--green` and `--red` CSS variables added to theme

### v34
- **fontFP gate removed from training** — warmUpWithLib now uses all library samples regardless of font fingerprint; gate was silently dropping vowels labeled at slightly different medH values
- **Margin threshold raised 0.08→0.12** — net now blanks uncertain matches rather than guessing wrong chars (fixes spurious `*` in output)
- Unused `fp` variable removed from warmUpWithLib

### v33
- **TextDetector removed** — Saccade always uses its own pipeline; no browser API fallback, fully browser-agnostic as intended
- **WARM UP progress span fixed** — dedicated `#warm-pct` element in HTML, no more re-creation on every callback tick
- **`labeledSamples` parameter removed** — was passed to `warmUpWithLib` but never used; cache check now only considers medH drift and library size

### v32
- **Freeze with existing library fixed** — autoMatch suggestions now computed lazily one cluster at a time with a `tick()` yield between each, instead of all 40 upfront blocking the UI thread
- **Library lookups 10-20× faster** — centroids and library samples pre-normalized at store/load time; autoMatchCluster uses dot product instead of full cosine (no sqrt per comparison)
- **sacatFromJSON** and **addToLib** both store a normalized `scaled` copy alongside raw pixels
- **loadLibFromLS** entries normalized lazily on first use if loaded from older format

### v31
- Gap fill threshold raised 0.30→0.50 — only shows chars where the image actually has a plausible match; no more being asked about `}` and `~` on a prose image
- Gap fill now only iterates chars that crossed the threshold — skips the rest entirely
- `autocapitalize="none"` on both label and gap fill inputs — mobile keyboard no longer auto-capitalises first char
- "USE BEST MATCH" renamed to "CONFIRM + ADD" for clarity

### v30
- **All clusters shown during LABEL** — no more hidden auto-matches; every cluster displayed with library suggestion pre-filled in input box; user confirms, corrects, or skips each one
- **DONE always available** — no minimum label count, no countdown; you label what you want and move on
- **Gap fill phase added** — after cluster labeling, any character with zero library coverage gets a reference render + best-match blob from the image; user confirms or marks "not in image"; builds library coverage organically
- **Synth removed** — training data is 100% real labeled blobs; no more synthetic interference with chars you've already labeled; `warmUpWithLib` is library-only
- **Net skipped cleanly when library empty** — WARM UP + QUANTIZE skip gracefully if library has no matching entries; blobLabels handles direct matches without net
- **Cluster threshold lowered 0.85→0.78** — P/F/R and similar stroke-sharing chars now split into separate clusters
- **Tab key skips cluster** — Tab/Escape both skip, Enter confirms

### v29
- **Label modal hang fixed** — stale localStorage library no longer silently auto-matches all clusters; `MIN_CONFIRM_FLOOR=5` always promotes at least 5 clusters to manual review
- **Pipeline freeze fixed** — `finish()` now resolves the Promise when clusters are exhausted even if minimum label count wasn't reached; `MIN_LABELS` adapts to cluster count
- **Labeling actually affects output** — labeled clusters now short-circuit neural net inference at MATCH time; blobs whose cluster was labeled get that char directly, no margin check, no uncertainty
- **CLEAR LIB button** — red button in lib bar; confirms before wiping; clears `sacatLib`, `localStorage`, and invalidates net cache
- **Net cache invalidation fixed** — `_trainedLibCount` tracks library size at training time; cache busts if library changed between runs
- **Dead loop removed** — stub `for(const[,ch] of labeledSamples)` with empty body removed from `warmUpWithLib`
- **Responsive layout** — `100dvh` for mobile address-bar correctness; panels stack vertically on ≤600px screens; lib-bar and output-bar wrap on narrow viewports; pipeline bar scrolls silently

### v28
- Fixed `.sacat` import: `fontFP` now preserved through export/import round-trip; imported entries no longer silently dropped at training time
- Confidence margin lowered 0.15→0.08 for better recall at 48×48 input resolution
- Epochs bumped 35→45 for better convergence

### v27
- Cluster previews now render at **native blob resolution** instead of upsampled 48×48 — eliminates scanline artifacts on dark-background images
- Native blob dimensions stored with cluster pixels throughout pipeline

### v26
- **48×48 input resolution** (up from 32×32) — 2.25× more discriminative pixels
- **TMAC ternary inference** — BitNet b1.58 absmean quantization, 3⁴=81 pattern lookup tables, 4× faster inference; new QUANTIZE stage in pipeline strip
- `P/R/F` disambiguation improved at higher resolution

### v25
- Minimum 20 labels required before DONE LABELING unlocks (counts down live)
- Max clusters raised 30→40
- Hull fill ratio filter added — removes bracket/corner fragment clusters before labeling

### v24
- Library samples capped at 20 per character to prevent frequency bias in training
- Confidence margin gate added to matchBlob — uncertain predictions emit nothing

### v23
- Cluster similarity threshold tuned to 0.85
- Ink density filter lowered to 5% — round letters no longer filtered out

### v22
- Font fingerprinting — each library entry tagged with hash of rendered reference chars; cross-font contamination prevented
- `.sacat` export now uses `application/octet-stream` MIME type (correct `.sacat` extension)

### v21
- Training speed 4-5min → ~90s: HIDDEN_DIM 128→64, SYNTH_PER_CHAR 40→15, EPOCHS 60→35
- Dot/tail blob merge pass added (fixes `i`, `j`, `!`, `?`, citation numbers)
- PROSE_PRIOR removed — library is the prior now

### v20
- `.sacat` persistent character library (localStorage + export/import)
- CLUSTER stage: greedy nearest-neighbor grouping by cosine similarity
- LABEL stage: interactive UI, 6 blob previews per cluster, confirm/skip flow
- WARM UP trains on library entries (weighted ×2) + synthetic augmentation
- Font fingerprinting via `computeFontFingerprint()`

### v19
- Neural classifier replaces profile-based matcher entirely
- TinyNet: 1024→128→95, trained on synthetic data at medH per image
- WARM UP stage added to pipeline

### v12–v18
- Profile-based matching engine iterations (8-angle projections, hole detection, PROSE_PRIOR, atlas font tuning)
- WAT kernel integration (standby mode)
- Preprocessing pipeline established and confirmed working

---

*ConsciousNode SoftWorks — Greenwood, South Carolina*
*Built by Kham and Vael Interim*
