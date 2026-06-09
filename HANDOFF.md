# Saccade — Handoff Document
*For Vael Interim, next session. Written by Vael Interim, June 8 2026.*

---

## What Saccade is

Single-file browser-native OCR. Zero external dependencies. Xinu compliant. The full tool lives in `Saccade.html`. No build step, no network calls, no pre-trained weights. It runs entirely in the browser, including the neural net training.

**Live:** `https://consciousnode.github.io/Saccade/Saccade.html`
**Repo:** `https://github.com/ConsciousNode/Saccade`

---

## Pipeline (v28)

```
INGEST → THRESH → SEGMENT → ATLAS → CLUSTER → LABEL → WARM UP → QUANTIZE → MATCH → EMIT
```

Each stage lights up green in the pipeline strip. The user sees progress live.

**INGEST:** Canvas drawImage → ImageData  
**THRESH:** Adaptive binarization, integral image, dark-bg auto-detect (flips if >50% ink)  
**SEGMENT:** Union-find connected components, size filter, dot/tail merge pass (fixes i/j/!/?)  
**ATLAS:** Legacy stage, currently a no-op placeholder kept for pipeline continuity  
**CLUSTER:** Greedy nearest-neighbor by cosine distance on 48×48 scaled pixels, hull fill filter (drops brackets/corners), up to 40 clusters, sorted by population  
**LABEL:** Interactive UI — shows 6 native-resolution blob previews per cluster, user types character, CONFIRM/SKIP/DONE LABELING. Minimum 20 labels before DONE unlocks (counts down). Auto-matches library entries with >90% cosine similarity if same font fingerprint.  
**WARM UP:** Trains TinyNet (2304→64→95) on library entries (weight ×2, capped 20/char) + synthetic augmented samples (15/char, 3 degradation variants). 45 epochs, cosine LR decay. Yields every 200 steps, progress shown on stage dot.  
**QUANTIZE:** Converts float32 L1 weights → ternary {-1,0,+1} via BitNet b1.58 absmean threshold. Builds TMAC lookup tables (3^4=81 patterns per 4-weight chunk, chunk size 4). 4× faster inference. L2 stays float32.  
**MATCH:** Each blob → scaleBin 48×48 → QuantizedNet forward → softmax → top-2 margin check. If margin < 0.08: emit nothing. If margin ≥ 0.08: emit character.  
**EMIT:** Lines assembled by groupLines (medH*0.55 vertical tolerance), word gaps by medW*0.45.

---

## Key data structures

**sacatLib:** `Map<char, Array<{pixels:Float32Array(2304), medH:number, source:'user'|'synth', timestamp:number, fontFP:string|null}>>`  
Persisted to localStorage (`saccade_atlas_v1`). Exported/imported as `.sacat` JSON.

**Font fingerprint:** Hash of rendered pixels of `agmrn` at medH in sans-serif. Computed once per session, cached in `_currentFontFP`. Reset on NEW IMAGE. Prevents cross-font contamination in training and auto-matching.

**Cluster pixel format:** Each cluster pixel entry is `{scaled:Float32Array(2304), nativeW:number, nativeH:number}`. The `scaled` field is what goes to the net. `nativeW/H` is for display only.

**TinyNet:** Float32 training net. `l1: LinearLayer(2304,64)`, `l2: LinearLayer(64,95)`. Kaiming init. Cross-entropy loss with softmax.

**QuantizedNet:** Post-training inference. `l1t: TernaryLayer` (TMAC lookup tables), `l2: LinearLayer` (float32, kept as-is since it's only 64×95=6080 ops).

---

## Known issues / active work

### P/R/F cluster contamination
Uppercase letters with vertical stroke + horizontal crossbar (`P`, `R`, `F`, `E`, `B`) still sometimes cluster together at 0.85 cosine threshold. The 48×48 resolution helps but doesn't fully solve it. Kham skips these correctly — they get labeled as unlabeled blobs and fall back to synth.

**Potential fix:** Aspect ratio gate on cluster membership — P is ~0.7 AR, F is ~0.6 AR, R is ~0.65 AR. Could split this cluster reliably. Not yet implemented.

### Output sparseness vs accuracy tradeoff
Current margin is 0.08. Output is sparse but more accurate. As the library grows (more sessions, more chars) the net gets more confident and output fills in. This is by design — the tool is honest about uncertainty.

### Dark-background images
The native-resolution cluster preview fix (v27) solved the scanline artifacts. However, dark-theme images (white text on black, e.g. notes apps, terminals) still need the user to go through a full labeling session since the font fingerprint will differ from any light-background library entries.

### The ATLAS stage
Currently does nothing in the pipeline — it's a placeholder from the pre-neural architecture. Could be repurposed to show library stats or a "warmup preview" — hasn't been prioritized.

---

## Architecture decisions worth knowing

**Why 48×48 not larger:** At 48×48 with TMAC, inference cost ≈ float32 at 32×32. Going larger (64×64) would require more than 45 epochs to converge, pushing warm-up past 2 minutes on mobile.

**Why TMAC chunk size 4:** 3^4=81 patterns is small enough to fit lookup tables in L1 cache on mobile. Chunk size 8 (3^8=6561 patterns) would be more accurate but table builds would take longer and cache efficiency drops.

**Why the library cap is 20:** English letter frequency distribution is extremely skewed — `e` can easily accumulate 80+ samples in one session while `z` gets 5. Capping at 20 per char equalizes training representation.

**Why font fingerprinting:** Serif vs sans-serif at the same medH produce completely different 48×48 profiles. Without fingerprinting, a `e` from a Wikipedia article contaminates a terminal OCR session. The hash is cheap (render 5 chars, sum pixel intensities) and reliable within a browser session.

---

## Files in repo

```
Saccade.html    — the entire tool (v28)
index.html      — GitHub Pages landing page
README.md       — documentation + changelog
HANDOFF.md      — this file
LICENSE         — license
```

---

## Next session priorities (Kham's notes from session)

1. **Test v28 import fix** — the `.sacat` import was silently dropping all entries due to missing `fontFP` in export. v28 fixes this. First order of business is confirming it works.

2. **Build up the library on the notes app image** — clean sans-serif, high contrast, consistent font. This image gives the cleanest clusters. A few sessions should get the library to 40+ chars with good coverage.

3. **P/R/F cluster split** — aspect ratio gating is the proposed fix. Worth implementing once the library is rich enough to test against.

4. **WAT kernel integration for segmentation** — the WASMKernal is embedded and booting but the connected-component labeling is still pure JS. Moving the union-find flood fill to WAT would free up significant JS time during SEGMENT. This was deferred repeatedly in favor of matching engine work.

5. **Second test image** — Wikipedia serif article has been the primary test case. Need to confirm the tool works on other image types: terminal output, PDF screenshots, printed text photos.

---

## Context on the collaboration

Kham is the founder/architect of ConsciousNode SoftWorks. He orchestrates; I (Vael) build. The working style is: Kham proposes direction, I propose before implementing, we iterate fast. Kham has a strong intuition for when something is architecturally wrong vs when it just needs tuning — trust that.

The CNS neural stack (FPSS, Simulacra, Brymar, HTMLNLM) is available for reference. The TMAC inference layer was pulled directly from FPSS's BitNet b1.58 implementation. LinearLayer and training loop from Simulacra. If you need more of the stack, ask Kham.

The xinu constraint is non-negotiable: single file, zero external deps, browser as bare metal. Everything gets built from scratch in vanilla JS + canvas.

This session ran from Saccade-12 through Saccade-28 — 16 versions in one sitting. The matching engine went through projection profiles, 8-angle histograms, cosine similarity with PROSE_PRIOR, atlas font tuning, and finally landed on the neural classifier with TMAC inference. The `.sacat` library system was designed by Kham and implemented this session.

Good luck. The goblin will cut you off. It's fine. Check the file state, verify what landed, keep going.

— Vael

