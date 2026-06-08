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

**SEGMENT** finds connected ink blobs in the binarized image using a union-find flood fill.

**CLUSTER** groups visually similar blobs by cosine distance on 48×48 pixel representations. The most populated clusters surface first — those are the most common characters in your image.

**LABEL** shows you each cluster: six example blobs rendered at native resolution. You type what character they show. The tool learns from you.

**WARM UP** trains a tiny two-layer neural network (`2304→64→95`) on your labeled samples plus synthetic augmentation, using cross-entropy loss and cosine LR decay. Runs in the background, yields to the UI every 200 steps, shows progress live.

**QUANTIZE** converts the trained float32 layer-1 weights to ternary `{-1, 0, +1}` using BitNet b1.58 absmean thresholding, then precomputes TMAC lookup tables (3⁴ = 81 patterns per 4-weight chunk). Inference becomes table lookups — no multiplies. 4× faster than float32 at 48×48 input resolution.

**MATCH** runs each blob through the quantized net. If the margin between top-1 and top-2 probability is below 0.15, the blob is skipped rather than guessed wrong.

## The library

Every labeling session builds your `.sacat` atlas file. Export it. Import it on any device. The library fingerprints each entry by font context — labels from a serif document won't contaminate a sans-serif one. Each subsequent run auto-matches previously labeled clusters, so the LABEL stage gets shorter over time.

```
📚 Library: 30 chars · 579 samples
```

## Usage

1. Open `Saccade.html` in any modern browser
2. Drop or select an image
3. Label the character clusters that appear (minimum 20 to unlock DONE LABELING)
4. Wait for WARM UP and QUANTIZE
5. Copy the extracted text

Export your `.sacat` library after labeling to keep it for future sessions.

## Philosophy

- **Single file.** The entire tool is `Saccade.html`. No build step. No dependencies. Copy it anywhere.
- **Xinu compliant.** Browser as bare metal. The only runtime is what ships with the browser.
- **Offline first.** Nothing leaves your device. The neural net trains locally, infers locally.
- **Browser agnostic.** Tested on Android Chrome. Designed for any modern engine.

## Technical lineage

Saccade is built on ConsciousNode's in-house neural stack:

- **TinyNet** — two-layer classifier (`LinearLayer`, ReLU, softmax cross-entropy) pulled from Simulacra's architecture
- **TMAC** — ternary matrix multiplication via lookup tables, derived from BitNet b1.58 and FPSS's ternary quantization
- **Adaptive threshold** — integral image Sauvola-style binarization
- **Union-find segmentation** — connected component labeling, dot/tail merge pass
- **Greedy nearest-neighbor clustering** — cosine similarity at 48×48, hull fill filter

No external libraries were used. No pre-trained weights were shipped.

## Development story

Saccade started as a projection-profile matcher — computing 8-angle ink histograms per blob and comparing them via cosine similarity against a rendered character atlas. This worked poorly. The profiles weren't discriminative enough at small sizes, and the atlas font never matched the screenshot font.

The v4 engine replaced the atlas entirely with a trained classifier. After segmentation, blobs are clustered by visual similarity and the user labels the clusters — teaching Saccade what characters actually look like in *this image*, at *this font*, at *this size*. The labeled samples become training data for a tiny neural net that warms up right there in the browser.

The TMAC quantization step came from asking: what from the ConsciousNode neural stack could help here? The answer was BitNet-style ternary inference. After float32 training, layer-1 weights compress to lookup tables. Inference at 48×48 costs the same compute as float32 at 32×32 — but with 2.25× more discriminative pixels.

The `.sacat` library format makes the tool accumulate intelligence across sessions. Each labeled image contributes to a persistent atlas that grows richer with use, indexed by font fingerprint so different font contexts don't contaminate each other.

Active development is ongoing. The architecture is stable; the accuracy is improving.

---

*ConsciousNode SoftWorks — Greenwood, South Carolina*  
*Built by Kham and Vael Interim*
