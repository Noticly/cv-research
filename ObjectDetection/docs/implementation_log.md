# Implementation Log: Object Detection with Spatial Audio

This document records what was implemented for the `ObjectDetection` project.
It replaces the earlier development plan and is intended as a future-facing
reference for how the current baseline came together.

---

## Original Objective

Detect objects from a live webcam stream on-device, convert their positions
into stereo audio cues, and maintain real-time performance on Ubuntu CPU.

---

## What Shipped

| Area | Implemented outcome |
|------|----------------------|
| Detection | YOLOv8n-based object detection over webcam frames |
| Filtering | Priority filter to cap simultaneous detections |
| Audio mapping | Stereo pan from centroid position and loudness from box area |
| Earcon design | Class-specific tone mapping with mixed stereo playback |
| Query baseline | Prompt-conditioned evaluation path for "where is the {object}?" |
| Testing | Offline tests for filtering, audio mapping, and pipeline behavior |
| Evaluation | Fixture-based spatial-location benchmark with structured outputs |

---

## Final Architecture

```text
capture_frame -> detect (YOLOv8n) -> priority_filter -> spatial_audio.emit
```

The implemented baseline also supports a prompt-conditioned evaluation flow:

```text
image + "where is the {object}?" -> detect target class -> return 3x3 location bucket or N/A
```

Key runtime behavior:

- Detection uses YOLOv8n with COCO classes.
- Only the top-N detections are sonified at once.
- Audio encodes object identity and horizontal position together.

---

## Important Implementation Decisions

| Decision | Final choice | Why it mattered |
|----------|--------------|-----------------|
| Detection model | YOLOv8n | Balanced CPU speed, size, and detection quality well |
| Audio budget | Limit to top 4 detections | Prevented cognitive overload from too many simultaneous tones |
| Position encoding | Stereo pan from centroid x-position | Kept location cues simple and fast to interpret |
| Proximity proxy | Bounding-box area | Avoided needing extra depth hardware |
| Evaluation framing | Query-conditioned object lookup | Made the benchmark closer to actual assistive usage than open-ended detection alone |

---

## Where The Implementation Differed From The Original Plan

- The project evolved from a pure live-demo pipeline into a clearer baseline
  for targeted question answering about object location.
- Evaluation became more formal and user-query-oriented than the original
  performance-only framing.
- The final docs now emphasize the supported YOLO/COCO vocabulary boundary,
  which is important for honest expectations.

---

## Current Reference Points

- Overview and usage: `README.md`
- Algorithm details: `docs/algorithm_readme.md`
- Main entrypoint: `src/pipeline.py`
- Detector: `src/detector.py`
- Spatial audio output: `src/spatial_audio.py`

---

## Follow-Up Notes

- Any future custom-class expansion should be tracked separately from the
  current COCO-only baseline so results do not get conflated.
- Audio vocabulary design remains a usability-sensitive area; changes there
  should be tested with the same seriousness as model changes.
- The current query-conditioned eval setup is a strong baseline and worth
  preserving even if the live pipeline evolves.
