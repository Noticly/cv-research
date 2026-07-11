# Implementation Log: Scene Description via VLM API

This document records what was implemented for the `SceneDescription` project.
It replaces the original forward-looking development plan and is intended as a
lightweight engineering history for future contributors.

---

## Original Objective

Build a webcam pipeline that captures frames at a configurable interval, sends
them to a vision-language model for short scene descriptions, and speaks the
result with a fallback path suitable for unreliable demo environments.

---

## What Shipped

| Area | Implemented outcome |
|------|----------------------|
| Frame capture | Webcam capture and JPEG/base64 encoding for VLM input |
| Remote inference | Anthropic and OpenAI backends behind one client interface |
| Fallbacks | Three-tier fallback chain: remote VLM, local Ollama/LLaVA, demo cache |
| Speech output | TTS pipeline with interruption behavior to avoid stale speech |
| Pipeline | Configurable CLI loop with backend override, interval override, and no-TTS mode |
| Testing | Offline test coverage for capture, client behavior, fallback logic, and pipeline flow |
| Evaluation | Static-image evaluation with LLM-judge scoring and versioned HTML/JSON outputs |

---

## Final Architecture

```text
capture_frame -> encode JPEG -> describe_scene (remote VLM)
                                -> on timeout/error: describe_scene_local
                                -> on failure: demo_cache.json
                                -> TTS
```

Key runtime behavior:

- Default backend is Anthropic, with OpenAI available as an override.
- Remote inference is bounded by a 5-second timeout.
- Local fallback uses Ollama/LLaVA for offline operation.
- Demo cache guarantees output even when both model paths fail.

---

## Important Implementation Decisions

| Decision | Final choice | Why it mattered |
|----------|--------------|-----------------|
| Remote model abstraction | Anthropic and OpenAI behind one interface | Kept the pipeline flexible without changing the main loop |
| Timeout handling | Normalize backend-specific timeout behavior to `TimeoutError` | Simplified fallback control flow |
| Offline fallback | Ollama/LLaVA before cached responses | Preserved some real image understanding when internet was unavailable |
| Speech interruption | Drain queue and speak only the latest description | Prevented stale scene narration during rapid updates |
| Demo resilience | Pre-recorded cache as final tier | Ensured the project always produced output during demos |

---

## Where The Implementation Differed From The Original Plan

- The project grew beyond a basic remote-VLM prototype into a resilient
  multi-tier pipeline with explicit timeout normalization and offline fallback.
- Evaluation became more structured than originally planned, with fixture-based
  runs and versioned HTML/JSON reports.
- The demo cache ended up as a formal fallback tier rather than just a loose
  contingency idea.

---

## Current Reference Points

- Overview and usage: `README.md`
- Algorithm details: `docs/algorithm_readme.md`
- Main entrypoint: `src/pipeline.py`
- Remote VLM client: `src/vlm_client.py`
- Offline fallback: `src/fallback.py`

---

## Follow-Up Notes

- This project is the only one in the research set with a cloud dependency in
  its primary path, so timeout and fallback behavior should remain central to
  future changes.
- If future work adds streaming or conversational follow-up, keep the current
  "short, direct, low-latency output" constraint visible so the UX stays
  aligned with assistive use.
- Any future evaluation expansion should preserve comparability with the
  existing fixture-based reporting format.
