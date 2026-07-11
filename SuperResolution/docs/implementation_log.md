# Implementation Log: On-Device Super-Resolution for Region Zoom

This document records what was implemented for the `SuperResolution` project.
It replaces the original development plan and now acts as a concise log of the
project's shipped baseline, decisions, and follow-up findings.

---

## Original Objective

Build an offline region-zoom pipeline for low-vision users that improves on
naive digital zoom by using lightweight super-resolution models and practical
on-device enhancement techniques.

---

## What Shipped

| Area | Implemented outcome |
|------|----------------------|
| Capture flow | ROI-based zoom-region selection for webcam frames |
| Baseline enhancement | Bilinear fallback plus adaptive sharpen and Laplacian edge enhancement |
| SR inference | FSRCNN and ESPCN implementations behind a shared wrapper |
| Pretrained baseline | Converted public pretrained checkpoints into repo-compatible weights |
| Pipeline | SR-enabled zoom path with no-SR fallback mode |
| Export path | ONNX export and quantization support |
| Benchmarking | PSNR/SSIM/latency comparison harness grouped by scale |
| Evaluation | Versioned HTML/JSON fixture evaluation against medicine-package images |

---

## Final Architecture

```text
capture_frame -> select_zoom_region -> crop -> SR upscale -> optional enhancement -> display
```

Fallback path:

```text
capture_frame -> select_zoom_region -> crop -> bilinear_upscale -> enhance -> display
```

Key runtime behavior:

- Super-resolution is applied to a user-selected region, not the full frame.
- Models operate on the luma channel only for speed and practical quality.
- Multiple pretrained baselines are supported across different scale factors.

---

## Important Implementation Decisions

| Decision | Final choice | Why it mattered |
|----------|--------------|-----------------|
| Region strategy | ROI-only zoom | Kept compute focused on what the user actually wants to inspect |
| Model set | ESPCN and FSRCNN | Provided a practical speed/quality tradeoff space |
| Color handling | Luma-only SR with bicubic chroma upsampling | Improved speed without sacrificing the details that matter most |
| Pretrained compatibility | Remap public checkpoints into local architecture | Made the project immediately usable before fine-tuning |
| Benchmark kernel | PIL bicubic for pretrained-checkpoint evaluation | Avoided misleading regressions caused by bicubic-kernel mismatch |

---

## Where The Implementation Differed From The Original Plan

- Pretrained checkpoint conversion became a major piece of the project, rather
  than just assuming working weights would be available.
- Evaluation exposed a non-obvious finding: hybrid post-enhancement can hurt a
  strong SR result even when it helps the bilinear fallback path.
- The project became more rigorous about data-generation conventions and color
  space details than the original plan anticipated.

---

## Current Reference Points

- Overview and usage: `README.md`
- Algorithm details: `docs/algorithm_readme.md`
- Main entrypoint: `src/pipeline.py`
- SR models: `src/sr_model.py`
- Benchmark harness: `src/benchmark.py`
- Pretrained conversion: `src/convert_pretrained.py`

---

## Follow-Up Notes

- Keep training/evaluation LR-generation kernels consistent with checkpoint
  provenance; this is a real quality risk, not a documentation detail.
- Hybrid enhancement should remain configurable because it is not universally
  beneficial.
- If future work fine-tunes models for text-heavy crops, compare against the
  current pretrained baselines explicitly rather than replacing them silently.
