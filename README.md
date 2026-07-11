# Noticly CV Research

This repository contains the computer vision research workspace for Noticly.
Its purpose is to explore, prototype, and evaluate CV algorithms that may be
used in Noticly products, especially assistive smart-glasses workflows for
blind and low-vision users.

Product-level mission, vision, and general Noticly context live in the main
project README at `noticly/README.md`. This repository is
specifically about research implementation: trying candidate approaches,
measuring behavior, documenting tradeoffs, and keeping useful baselines for
future product integration.

---

## Repository Purpose

This repo is where we:

- prototype vision pipelines that support real assistive tasks
- compare algorithm choices under practical constraints such as CPU-only,
  offline operation, latency, and demo reliability
- build evaluation harnesses and fixture sets for repeatable testing
- document implementation details and lessons learned for future engineering work

This is a research and validation repo, not the final product application.

---

## Research Areas

The current workspace includes four project areas:

| Project | Focus | Typical output |
|---|---|---|
| `SceneDescription/` | Scene understanding with VLMs and fallback paths | Spoken natural-language description |
| `OCR/` | On-device text recognition | Spoken recognized text |
| `ObjectDetection/` | Object localization with spatial audio | Earcons encoding identity and position |
| `SuperResolution/` | Region zoom enhancement for low-vision users | Enlarged, enhanced image crop |

These projects cover both audio-first assistance and visual enhancement.

---

## Research Principles

The projects in this repo are evaluated against practical product constraints:

- **Assistive usefulness first**: success is defined by whether the output helps
  a user complete a real task, not just by benchmark scores.
- **Offline where possible**: OCR, object detection, and super-resolution are
  designed to work locally when practical.
- **Fallbacks matter**: cloud-dependent systems must degrade gracefully.
- **Honest scope**: baselines should clearly state what they do and do not
  support.
- **Repeatable evaluation**: fixture-based tests and reports should make future
  comparisons easy.

---

## Documentation Map

Start here depending on what you need:

- Repo overview: `docs/research_overview.md`
- Project setup and usage: each project's `README.md`
- Algorithm details: each project's `docs/algorithm_readme.md`
- Implementation history: each project's `docs/implementation_log.md`

---

## Project Structure

```text
noticly-cv-research/
├── docs/               Shared research documentation
├── OCR/                On-device OCR research
├── ObjectDetection/    Object detection and spatial audio research
├── SceneDescription/   Scene description / VLM research
└── SuperResolution/    Region zoom and super-resolution research
```

---

## How To Use This Repo

1. Choose a project folder based on the capability you want to inspect.
2. Read that project's `README.md` for setup and usage.
3. Read `docs/algorithm_readme.md` for implementation details and design
   rationale.
4. Use the project's test and eval scripts to reproduce current behavior.

If you are orienting across the whole workspace first, read
`docs/research_overview.md`.

---

## Relationship To Noticly Product Work

This repository is an upstream research layer for Noticly product development.
Its role is to reduce uncertainty before algorithms are integrated into product
codebases. A project here is useful when it does at least one of the following:

- demonstrates a viable baseline for a user-facing capability
- identifies a limitation early and documents it clearly
- produces a reusable eval harness or fixture set
- clarifies tradeoffs between local, cloud, latency, and quality constraints

---

## Contribution Style

Changes in this repo should keep the research trail legible:

- prefer clear baselines over premature complexity
- document major implementation decisions
- keep evaluation results reproducible
- state limitations directly
- avoid overstating readiness for real-world deployment

---

## Related Repo

- Main Noticly project: `noticly/README.md`
