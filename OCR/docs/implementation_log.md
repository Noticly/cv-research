# Implementation Log: On-Device OCR

This document records what was implemented for the `OCR` project. It replaces
the original development plan and now serves as a compact engineering log for
future maintenance and iteration.

---

## Original Objective

Build a fully offline OCR pipeline that captures camera frames, isolates the
relevant region, preprocesses the image, runs PaddleOCR, reconstructs readable
text order, and speaks the result.

---

## What Shipped

| Area | Implemented outcome |
|------|----------------------|
| Capture workflow | Webcam capture with on-demand and continuous modes |
| Targeting | ROI-based capture path to avoid noisy full-frame OCR |
| Preprocessing | Orientation-aware preprocessing pipeline rather than simple deskew-only flow |
| Recognition | PaddleOCR wrapper with confidence filtering |
| Text structuring | Reading-order reconstruction from token boxes |
| Speech output | Offline TTS with interruption behavior |
| Testing | Offline unit/integration tests that do not require camera access or model weights |
| Evaluation | Fixture-based evaluation with CER and key-phrase recall modes |

---

## Final Architecture

```text
capture_frame -> pick_orientation -> PaddleOCR -> structure_text -> TTS
```

Key runtime behavior:

- Default interaction is on-demand capture.
- OCR runs fully on-device with no network dependency.
- Orientation handling uses a two-phase approach:
  projection-profile variance first, OCR-confidence tiebreaking second.

---

## Important Implementation Decisions

| Decision | Final choice | Why it mattered |
|----------|--------------|-----------------|
| OCR engine | PaddleOCR on CPU | Gave the best practical accuracy/runtime tradeoff for this project |
| Frame targeting | ROI before OCR | Avoided garbage results from busy full-frame scenes |
| Orientation handling | Variance scoring plus OCR-confidence tiebreak | Solved cases where simple geometry could not distinguish 0/180 or 90/270 |
| Text ordering | Bounding-box grouping into lines | Produced usable spoken output from token-level OCR results |
| Eval strategy | CER for ordered text, key-phrase recall for curved/scattered text | Matched the actual strengths and limits of the pipeline |

---

## Where The Implementation Differed From The Original Plan

- Orientation detection became more sophisticated than the initial
  preprocess-and-deskew concept.
- Evaluation expanded beyond a simple demo check into two distinct scoring
  modes for different surface types.
- The project had to explicitly account for curved packaging and reading-order
  failure cases, which became a documented limitation rather than an implicit
  edge case.

---

## Current Reference Points

- Overview and usage: `README.md`
- Algorithm details: `docs/algorithm_readme.md`
- Main entrypoint: `src/pipeline.py`
- OCR engine: `src/ocr_engine.py`
- Text structuring: `src/text_formatter.py`

---

## Follow-Up Notes

- Curved-surface reading order remains the clearest limitation and is the most
  likely place for future research improvements.
- If the project expands to more languages or more packaging types, preserve
  the current evaluation split so results stay interpretable.
- The current offline-first design is one of this module's main strengths and
  should not be diluted casually.
