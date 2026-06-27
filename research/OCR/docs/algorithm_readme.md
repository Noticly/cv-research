# Algorithm Reference — OCR

Captures a camera frame, extracts text using PaddleOCR, and speaks the result
via TTS.

```
capture_frame → correct_orientation → PaddleOCR → structure_text → TTS
```

---

## 1. Orientation Detection — Horizontal Projection Profile Variance

Before running OCR, the image is rotated to ensure text rows are horizontal.
The algorithm scores each of the four cardinal orientations (0°, 90°, 180°,
270°) and picks the one with the **highest row-sum variance** on a binarised
version of the image.

### Why variance of the row-sum profile?

When text rows are horizontal, the binary image has alternating bands of high
ink density (the text rows) and low ink density (the gaps between rows). The
horizontal projection profile (sum of pixel values per row) therefore oscillates
strongly, producing high variance. For a 90°-rotated image the same ink is
spread across columns instead of rows, the row-sum profile is nearly flat, and
variance is low.

### Algorithm (`src/preprocess.py: detect_orientation`)

1. Convert to grayscale.
2. Downsample so the longest side is at most 600 px (speed).
3. Apply Gaussian blur (5×5) then Otsu thresholding — produces a binary image
   with ink pixels = 255.
4. For each candidate angle ∈ {0°, 90°, 180°, 270°}:
   - Rotate the binary image with `cv2.rotate`.
   - Compute the horizontal projection: `profile[i] = sum of row i`.
   - Compute `var(profile)`.
5. Return the angle with the highest variance.

```python
profile = np.sum(candidate, axis=1, dtype=np.float64)
var = float(np.var(profile))
```

### Correction (`src/preprocess.py: correct_orientation`)

Once the angle is known, apply the matching `cv2.rotate` code to the original
full-resolution image before passing it to PaddleOCR.

---

## 2. PaddleOCR Recognition

PaddleOCR (v2.9, engine: `paddlepaddle==2.6.2`) runs a three-stage pipeline
internally:

1. **Text detection** (DB-MobileNetV3) — finds bounding polygons around text
   regions.
2. **Angle classifier** — predicts 0° vs 180° orientation per word crop.
3. **Text recognition** (CRNN) — reads the character sequence from each crop.

The wrapper (`src/ocr_engine.py: recognize`) filters results by a confidence
threshold (default 0.6) and returns a list of token dicts:

```python
{"text": str, "confidence": float, "bbox": list[list[float]]}
```

---

## 3. Reading-Order Reconstruction

Tokens are sorted into reading order by `src/text_formatter.py: structure_text`:

1. Sort tokens by `(min_y, min_x)` of their bounding box.
2. Group tokens into lines using vertical overlap: two tokens belong to the same
   line if their bounding boxes overlap by more than −10 px vertically.
3. Within each line, sort tokens left-to-right by `min_x`.
4. Join tokens per line with spaces; join lines with newlines.

### Known limitation — curved surfaces

On cylindrical packaging (e.g. medicine tubes), all text lines wrap around the
surface and appear at nearly the same y-coordinate in the 2D projection. The
top-to-bottom, left-to-right sort cannot recover the correct reading order in
this case. Fixing it would require either a 3D unwrap step or a learned
reading-order model.

---

## 4. Text-to-Speech

A daemon thread (`src/tts.py`) drains a priority queue. Each call to `speak()`
enqueues the text. If a new item arrives while speech is in progress, the queue
is drained and only the latest item is spoken — stale descriptions are skipped.

---

## 5. Evaluation — Character Error Rate (CER)

CER measures OCR accuracy at the character level. It is the Levenshtein edit
distance between the recognised string and the ground truth, divided by the
length of the ground truth:

```
CER = edit_distance(reference, hypothesis) / len(reference)
```

The **edit distance** is the minimum number of single-character **insertions**,
**deletions**, and **substitutions** needed to transform the hypothesis into the
reference. It is computed with standard dynamic programming in O(|ref| × |hyp|)
time.

### Why CER instead of Word Error Rate (WER)?

WER penalises an entire word for a single wrong character. CER is more
informative for OCR because partial reads are common — a smudged digit, a
serif-vs-sans ambiguity, or a confidence-filtered token all produce partial
errors that WER over-penalises.

### Interpretation

| CER    | Quality               |
|--------|-----------------------|
| 0%     | Perfect match         |
| < 10%  | Excellent (printed text, flat surface) |
| 10–30% | Acceptable (challenging lighting, angle) |
| 30–60% | Poor — significant errors |
| > 100% | Hypothesis much longer than reference (hallucinated tokens) |

CER can exceed 100% because the denominator is fixed at `len(reference)` but
the hypothesis can be arbitrarily long.

### Benchmark fixtures

| Fixture set         | Images | Surface type        | Notes |
|---------------------|--------|---------------------|-------|
| `demo_docs/`        | 3      | Flat printed pages  | Baseline; controlled lighting |
| `book_cover/`       | 3      | Flat glossy cover   | Variable font sizes |
| `medicine_package/` | 3      | Flat box + cylindrical tube | Most challenging; curved surface disrupts reading order |

Ground truth files use the format `filename: expected text`, one line per image.
CER is computed case-insensitively.

---

## 6. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| OCR engine | PaddleOCR 2.9 / PaddlePaddle 2.6.2 | v3.x incompatible with this CPU's oneDNN |
| Orientation detection | Projection-profile variance | No ML model needed; works on any binary image |
| OCR confidence threshold | 0.6 | Empirically reduces noise on medicine labels |
| Evaluation metric | CER (not WER) | Fairer for partial OCR reads and short labels |
| TTS interruption | Daemon thread + priority queue; drain on wakeup | Avoids stale descriptions when scene changes |
