# Noticly Research Overview

This document summarizes the computer-vision research projects in this
repository. It replaces the original implementation plan now that the core
projects have been built and documented in their own folders.

Each project is a self-contained prototype with its own code, tests, and
algorithm notes. This overview is the quickest way to understand how the
projects fit together and where to go next for details.

---

## Project Summary

| Project | Purpose | Runtime profile | Primary docs |
|--------|---------|-----------------|--------------|
| SceneDescription | Describe what is in front of the user in natural language | Hybrid: remote VLM first, local fallback available | `SceneDescription/README.md`, `SceneDescription/docs/algorithm_readme.md` |
| OCR | Read text from camera frames and speak it aloud | Fully on-device, offline | `OCR/README.md`, `OCR/docs/algorithm_readme.md` |
| ObjectDetection | Detect objects and convey their positions through spatial audio | Fully on-device, offline | `ObjectDetection/README.md`, `ObjectDetection/docs/algorithm_readme.md` |
| SuperResolution | Magnify a selected region with higher fidelity than naive digital zoom | Fully on-device, offline | `SuperResolution/README.md`, `SuperResolution/docs/algorithm_readme.md` |

---

## How The Projects Fit Together

These four projects explore complementary ways to make first-person visual
information more accessible for blind and low-vision users:

- `SceneDescription` handles open-ended scene understanding and natural-language
  summarization.
- `OCR` focuses on high-confidence text extraction from signs, labels, and
  documents.
- `ObjectDetection` turns object identity and location into non-visual spatial
  audio cues.
- `SuperResolution` improves visual clarity for users who benefit from zooming
  into a small region rather than receiving audio output.

Together they cover both audio-first and vision-enhancement use cases.

---

## Comparison At A Glance

| Dimension | SceneDescription | OCR | ObjectDetection | SuperResolution |
|-----------|------------------|-----|-----------------|-----------------|
| Main input | Camera frame | Camera frame or ROI | Camera frame | User-selected ROI |
| Main output | Spoken scene description | Spoken recognized text | Spatial audio earcons | Enlarged enhanced image |
| Network required | Sometimes | No | No | No |
| Core technique | Vision-language model with fallback chain | PaddleOCR + reading-order reconstruction | YOLOv8n + priority filter + stereo mapping | FSRCNN/ESPCN + enhancement pipeline |
| User value | General awareness | Reading text | Finding and locating objects | Seeing small details more clearly |

---

## Recommended Reading Order

If you are new to the repo:

1. Start with the root `README.md` for product context and project structure.
2. Read the project `README.md` for setup, usage, and tests.
3. Read each `docs/algorithm_readme.md` for implementation details and design
   rationale.

Suggested project order for technical orientation:

1. `OCR` or `ObjectDetection` for fully local pipelines
2. `SceneDescription` for cloud-plus-fallback architecture
3. `SuperResolution` for model and image-quality evaluation work

---

## Current Status

- The original three planned projects are implemented.
- A fourth project, `SuperResolution`, has been added to study on-device region
  zoom for low-vision users.
- Detailed implementation guidance now lives inside each project folder, so
  this document intentionally stays high level.

---

## Historical Note

This file was originally a forward-looking plan for three research projects.
It now serves as a stable overview document for the implemented research
workspace.
