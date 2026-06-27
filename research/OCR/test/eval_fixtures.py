"""
Evaluate OCR accuracy against all fixture sets that contain a ground_truth.txt.

Usage (from the research/OCR directory):
    python test/eval_fixtures.py                    # all fixture subfolders
    python test/eval_fixtures.py --fixture medicine_package

For each fixture subfolder the script:
  - Runs OCR via src.ocr_engine.recognize() (includes orientation correction).
  - Computes per-image Character Error Rate (CER).
  - Prints a detailed report to stdout.
  - Saves eval_<commit>.json and eval_<commit>.html to the fixture subfolder.
    The HTML report embeds annotated images (bounding boxes overlaid) and a
    per-token table so results can be reviewed without running the script again.
"""

import argparse
import base64
import html as _html
import json
import os
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

FIXTURE_ROOT = _PROJECT_ROOT / "test" / "fixtures"
PASS_THRESHOLD = 0.30

# RGB palette shared between image annotation and HTML token colours.
# Index i → token i on the image and in the HTML table.
_PALETTE: list[tuple[int, int, int]] = [
    (255, 204,   0),  # amber
    (  0, 200,  80),  # green
    ( 30, 120, 255),  # blue
    (255,  60,  80),  # red
    (180,   0, 240),  # purple
    (255, 140,   0),  # orange
    (  0, 180, 180),  # teal
    (255, 100, 160),  # pink
]


def _palette_hex(i: int) -> str:
    r, g, b = _PALETTE[i % len(_PALETTE)]
    return f"#{r:02x}{g:02x}{b:02x}"


def _palette_bgr(i: int) -> tuple[int, int, int]:
    r, g, b = _PALETTE[i % len(_PALETTE)]
    return (b, g, r)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def _cer(ref: str, hyp: str) -> float:
    ref, hyp = ref.lower(), hyp.lower()
    r, h = len(ref), len(hyp)
    if r == 0:
        return 0.0 if h == 0 else 1.0
    dp = list(range(h + 1))
    for i in range(1, r + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, h + 1):
            dp[j] = prev[j - 1] if ref[i - 1] == hyp[j - 1] else 1 + min(prev[j], dp[j - 1], prev[j - 1])
    return dp[h] / r


def _load_ground_truth(gt_path: Path) -> dict[str, str]:
    gt = {}
    with open(gt_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fname, _, text = line.partition(": ")
            gt[fname.strip()] = text.strip()
    return gt


def _ocr_image(img_path: Path) -> tuple[str, list[dict]]:
    import cv2
    from src.ocr_engine import recognize
    from src.text_formatter import format_for_speech, structure_text

    img = cv2.imread(str(img_path))
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {img_path}")

    h, w = img.shape[:2]
    max_side = 2000
    if max(h, w) > max_side:
        scale = max_side / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    tokens = recognize(img)
    text = format_for_speech(structure_text(tokens))
    return text, tokens


# ---------------------------------------------------------------------------
# Image annotation
# ---------------------------------------------------------------------------

def _annotate_image_b64(img_path: Path, tokens: list[dict]) -> str:
    """Return base64-encoded JPEG with coloured bounding boxes overlaid.

    Bboxes are in the coordinate space of the OCR pipeline (max 2000 px on the
    longest side), so the image is resized the same way before drawing.
    The annotated image is then scaled down to max 1000 px for the HTML report.
    """
    import cv2
    import numpy as np

    img = cv2.imread(str(img_path))
    if img is None:
        return ""

    # Match the resize applied inside _ocr_image so bbox coords align.
    h, w = img.shape[:2]
    ocr_max = 2000
    if max(h, w) > ocr_max:
        scale = ocr_max / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    if tokens:
        overlay = img.copy()
        for i, tok in enumerate(tokens):
            pts = np.array([[int(p[0]), int(p[1])] for p in tok["bbox"]], dtype=np.int32)
            cv2.fillPoly(overlay, [pts], _palette_bgr(i))
        cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)

        for i, tok in enumerate(tokens):
            pts = np.array([[int(p[0]), int(p[1])] for p in tok["bbox"]], dtype=np.int32)
            bgr = _palette_bgr(i)
            cv2.polylines(img, [pts], True, bgr, 2)

            # Numbered label box at the top-left corner of the bbox.
            x = int(pts[:, 0].min())
            y = int(pts[:, 1].min())
            label = str(i + 1)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            pad = 3
            cv2.rectangle(img, (x, y - th - 2 * pad), (x + tw + 2 * pad, y), bgr, -1)
            cv2.putText(
                img, label, (x + pad, y - pad),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA,
            )

    # Scale down for the HTML report (smaller file size).
    h2, w2 = img.shape[:2]
    display_max = 1000
    if max(h2, w2) > display_max:
        ds = display_max / max(h2, w2)
        img = cv2.resize(img, (int(w2 * ds), int(h2 * ds)))

    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return base64.b64encode(buf.tobytes()).decode()


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def _explain(fixture_name: str, image_results: list[dict], mean_cer: float) -> str:
    passed = [r for r in image_results if r["passed"]]
    failed = [r for r in image_results if not r["passed"]]

    if not failed:
        best = min(image_results, key=lambda r: r["cer"])
        worst = max(image_results, key=lambda r: r["cer"])
        return (
            f"All {len(image_results)} images passed the {PASS_THRESHOLD:.0%} CER threshold. "
            f"Best: {best['filename']} ({best['cer']:.1%}). "
            f"Worst: {worst['filename']} ({worst['cer']:.1%})."
        )

    fail_names = ", ".join(f"{r['filename']} ({r['cer']:.1%})" for r in failed)
    pass_names = (
        ", ".join(f"{r['filename']} ({r['cer']:.1%})" for r in passed)
        if passed else "none"
    )

    modes = []
    empty = [r for r in failed if r["token_count"] == 0]
    order_errors = [r for r in failed if r["token_count"] > 0 and r["cer"] > 0.60]
    partial = [r for r in failed if r["token_count"] > 0 and r["cer"] <= 0.60]

    if empty:
        modes.append(f"no tokens detected ({', '.join(r['filename'] for r in empty)})")
    if order_errors:
        modes.append(
            "high CER despite tokens detected — likely reading-order errors on "
            f"curved/rotated surfaces ({', '.join(r['filename'] for r in order_errors)})"
        )
    if partial:
        modes.append(
            f"partial recognition — some tokens missing or substituted "
            f"({', '.join(r['filename'] for r in partial)})"
        )

    mode_str = "; ".join(modes) if modes else "undiagnosed"

    return (
        f"Mean CER {mean_cer:.1%} exceeds the {PASS_THRESHOLD:.0%} threshold. "
        f"Failed: {fail_names}. "
        f"Passed: {pass_names}. "
        f"Failure mode(s): {mode_str}."
    )


# ---------------------------------------------------------------------------
# Per-fixture evaluation
# ---------------------------------------------------------------------------

def evaluate_fixture(fixture_dir: Path, commit: str) -> dict:
    gt = _load_ground_truth(fixture_dir / "ground_truth.txt")

    image_results = []
    total_cer = 0.0

    for fname, expected in gt.items():
        img_path = fixture_dir / fname
        t0 = time.perf_counter()
        try:
            recognized, tokens = _ocr_image(img_path)
            error = None
        except Exception as exc:
            recognized, tokens, error = "", [], str(exc)
        elapsed = time.perf_counter() - t0

        c = _cer(expected, recognized)
        total_cer += c

        image_results.append({
            "filename": fname,
            "expected": expected,
            "recognized": recognized,
            "token_count": len(tokens),
            "tokens": [
                {
                    "text": t["text"],
                    "confidence": round(t["confidence"], 4),
                    "bbox": t["bbox"],
                }
                for t in tokens
            ],
            "cer": round(c, 4),
            "passed": c < PASS_THRESHOLD,
            "elapsed_s": round(elapsed, 3),
            **({"error": error} if error else {}),
        })

    mean_cer = total_cer / len(image_results) if image_results else 0.0
    verdict = "PASS" if mean_cer < PASS_THRESHOLD else "NEEDS IMPROVEMENT"
    explanation = _explain(fixture_dir.name, image_results, mean_cer)

    return {
        "fixture": fixture_dir.name,
        "commit": commit,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "threshold_cer": PASS_THRESHOLD,
        "mean_cer": round(mean_cer, 4),
        "verdict": verdict,
        "explanation": explanation,
        "images": image_results,
    }


# ---------------------------------------------------------------------------
# Stdout report
# ---------------------------------------------------------------------------

def _print_report(result: dict) -> None:
    w = 72
    print("=" * w)
    print(f"{'Fixture: ' + result['fixture']:^{w}}")
    print(f"{'Commit: ' + result['commit']:^{w}}")
    print("=" * w)

    for img in result["images"]:
        print(f"\n{'─' * w}")
        print(f"  Image      : {img['filename']}")
        print(f"  Expected   : {img['expected']}")
        print(f"  Recognized : {img['recognized'] or '(empty)'}")
        print(f"  Tokens     : {img['token_count']} detected")
        if img["tokens"]:
            for tok in img["tokens"]:
                print(f"               [{tok['confidence']:.2f}] {tok['text']!r}")
        print(f"  CER        : {img['cer']:.1%}  {'✓ PASS' if img['passed'] else '✗ FAIL'}")
        print(f"  Elapsed    : {img['elapsed_s']:.2f}s")
        if "error" in img:
            print(f"  Error      : {img['error']}")

    print(f"\n{'─' * w}")
    print(f"  Mean CER   : {result['mean_cer']:.1%}")
    print(f"  Verdict    : {result['verdict']}  (threshold < {result['threshold_cer']:.0%})")
    print(f"\n  {result['explanation']}")
    print("=" * w)


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, -apple-system, sans-serif; background: #f3f4f6; color: #1f2937; }

header {
  background: #111827;
  color: #f9fafb;
  padding: 1.25rem 2rem;
  display: flex;
  align-items: baseline;
  gap: 1.5rem;
}
header h1 { font-size: 1.25rem; font-weight: 700; }
header .meta { font-size: 0.8rem; color: #9ca3af; font-family: monospace; }

.container { max-width: 1280px; margin: 0 auto; padding: 1.5rem; }

/* Summary */
.summary {
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.75rem;
  border-left: 5px solid;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.summary.pass { background: #f0fdf4; border-color: #22c55e; }
.summary.fail { background: #fff7ed; border-color: #f97316; }
.summary-top { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.verdict-badge {
  font-size: 0.7rem; font-weight: 800; letter-spacing: 0.08em;
  padding: 0.2rem 0.55rem; border-radius: 4px; text-transform: uppercase;
}
.verdict-badge.pass { background: #22c55e; color: #fff; }
.verdict-badge.fail { background: #f97316; color: #fff; }
.mean-cer { font-size: 2rem; font-weight: 800; line-height: 1; }
.mean-cer.pass { color: #16a34a; }
.mean-cer.fail { color: #ea580c; }
.threshold-note { font-size: 0.8rem; color: #6b7280; }
.explanation { font-size: 0.875rem; color: #4b5563; line-height: 1.6; }

/* CER legend */
.cer-legend {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1.75rem;
  font-size: 0.8rem;
  color: #6b7280;
}
.cer-legend strong { color: #374151; }
.cer-legend .bands { display: flex; gap: 1.5rem; margin-top: 0.4rem; flex-wrap: wrap; }
.band { display: flex; align-items: center; gap: 0.35rem; }
.band-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

/* Image cards */
.image-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 1.5rem;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 1rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}
.filename { font-weight: 700; font-family: monospace; font-size: 0.9rem; }
.card-header-right { display: flex; align-items: center; gap: 0.75rem; }
.elapsed { font-size: 0.75rem; color: #9ca3af; }
.cer-badge {
  font-size: 0.8rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 5px;
}
.cer-badge.pass { background: #dcfce7; color: #15803d; }
.cer-badge.fail { background: #ffedd5; color: #c2410c; }

.card-body { display: flex; min-height: 0; }

.image-col {
  flex: 0 0 46%;
  padding: 1rem;
  border-right: 1px solid #e5e7eb;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: #f9fafb;
}
.image-col img { max-width: 100%; border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.15); }
.image-col .no-image { color: #9ca3af; font-style: italic; font-size: 0.85rem; align-self: center; }

.text-col { flex: 1; padding: 1rem; display: flex; flex-direction: column; gap: 0.9rem; overflow: auto; }

.text-block label {
  display: block; font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: #9ca3af; margin-bottom: 0.3rem;
}
.text-block p { font-size: 0.875rem; line-height: 1.6; }
.text-expected p  { color: #111827; }
.text-recognized p { color: #2563eb; }
.text-recognized .empty { color: #9ca3af; font-style: italic; }

.error-box {
  background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px;
  padding: 0.5rem 0.75rem; font-size: 0.8rem; color: #b91c1c; font-family: monospace;
}

.token-section label {
  display: block; font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: #9ca3af; margin-bottom: 0.4rem;
}
.no-tokens { font-size: 0.82rem; color: #9ca3af; font-style: italic; }

.token-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.token-table th {
  text-align: left; padding: 0.3rem 0.5rem;
  background: #f9fafb; border-bottom: 1px solid #e5e7eb;
  font-weight: 600; color: #6b7280;
}
.token-table td { padding: 0.3rem 0.5rem; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }
.token-table tr:last-child td { border-bottom: none; }
.token-num { display: flex; align-items: center; gap: 0.4rem; }
.color-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.token-text { font-family: monospace; }
.conf { font-weight: 600; }
.conf-high { color: #16a34a; }
.conf-med  { color: #ca8a04; }
.conf-low  { color: #dc2626; }

@media (max-width: 800px) {
  .card-body { flex-direction: column; }
  .image-col { flex: none; border-right: none; border-bottom: 1px solid #e5e7eb; }
}
"""


def _conf_class(conf: float) -> str:
    if conf >= 0.90:
        return "conf-high"
    if conf >= 0.70:
        return "conf-med"
    return "conf-low"


def _render_image_card(img_result: dict, fixture_dir: Path) -> str:
    fname = img_result["filename"]
    passed = img_result["passed"]
    badge_cls = "pass" if passed else "fail"
    symbol = "✓" if passed else "✗"
    cer_pct = f"{img_result['cer']:.1%}"

    b64 = _annotate_image_b64(fixture_dir / fname, img_result["tokens"])
    img_tag = (
        f'<img src="data:image/jpeg;base64,{b64}" alt="{_html.escape(fname)}">'
        if b64
        else '<span class="no-image">Image unavailable</span>'
    )

    recognized_html = (
        f'<p>{_html.escape(img_result["recognized"])}</p>'
        if img_result["recognized"]
        else '<p class="empty">(no text recognised)</p>'
    )

    error_html = (
        f'<div class="error-box">Error: {_html.escape(img_result["error"])}</div>'
        if "error" in img_result
        else ""
    )

    if img_result["tokens"]:
        rows = ""
        for i, tok in enumerate(img_result["tokens"]):
            dot_color = _palette_hex(i)
            cc = _conf_class(tok["confidence"])
            rows += (
                f"<tr>"
                f'<td class="token-num">'
                f'<span class="color-dot" style="background:{dot_color}"></span>{i+1}</td>'
                f'<td class="token-text">{_html.escape(tok["text"])}</td>'
                f'<td class="conf {cc}">{tok["confidence"]:.2f}</td>'
                f"</tr>"
            )
        token_html = (
            f'<table class="token-table">'
            f"<thead><tr><th>#</th><th>Text</th><th>Conf.</th></tr></thead>"
            f"<tbody>{rows}</tbody>"
            f"</table>"
        )
    else:
        token_html = '<span class="no-tokens">No tokens detected above confidence threshold.</span>'

    return f"""
<div class="image-card">
  <div class="card-header">
    <span class="filename">{_html.escape(fname)}</span>
    <div class="card-header-right">
      <span class="elapsed">{img_result['elapsed_s']:.2f}s</span>
      <span class="cer-badge {badge_cls}">{symbol} CER {cer_pct}</span>
    </div>
  </div>
  <div class="card-body">
    <div class="image-col">{img_tag}</div>
    <div class="text-col">
      <div class="text-block text-expected">
        <label>Expected</label>
        <p>{_html.escape(img_result['expected'])}</p>
      </div>
      <div class="text-block text-recognized">
        <label>Recognised</label>
        {recognized_html}
      </div>
      {error_html}
      <div class="token-section">
        <label>Tokens ({img_result['token_count']} detected)</label>
        {token_html}
      </div>
    </div>
  </div>
</div>"""


def _render_html(result: dict, fixture_dir: Path) -> str:
    passed = result["verdict"] == "PASS"
    summary_cls = "pass" if passed else "fail"
    mean_cer_pct = f"{result['mean_cer']:.1%}"
    ts = result["timestamp"].replace("T", " ").replace("+00:00", " UTC")

    image_cards = "\n".join(
        _render_image_card(img, fixture_dir) for img in result["images"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OCR Eval — {_html.escape(result['fixture'])} @ {_html.escape(result['commit'])}</title>
  <style>{_CSS}</style>
</head>
<body>
<header>
  <h1>OCR Evaluation &mdash; {_html.escape(result['fixture'])}</h1>
  <span class="meta">commit {_html.escape(result['commit'])} &nbsp;·&nbsp; {_html.escape(ts)}</span>
</header>

<div class="container">

  <div class="summary {summary_cls}">
    <div class="summary-top">
      <span class="verdict-badge {summary_cls}">{_html.escape(result['verdict'])}</span>
      <span class="mean-cer {summary_cls}">{mean_cer_pct}</span>
      <span class="threshold-note">mean CER &nbsp;(threshold &lt; {result['threshold_cer']:.0%})</span>
    </div>
    <p class="explanation">{_html.escape(result['explanation'])}</p>
  </div>

  <div class="cer-legend">
    <strong>Character Error Rate (CER)</strong> — edit distance between recognised and
    expected text, divided by the length of the expected text.
    Lower is better; 0% = perfect match.
    <div class="bands">
      <span class="band"><span class="band-dot" style="background:#16a34a"></span>&lt; 10% excellent</span>
      <span class="band"><span class="band-dot" style="background:#ca8a04"></span>10–30% acceptable</span>
      <span class="band"><span class="band-dot" style="background:#ea580c"></span>30–60% poor</span>
      <span class="band"><span class="band-dot" style="background:#dc2626"></span>&gt; 60% failing</span>
      <span class="band"><span class="band-dot" style="background:#7c3aed"></span>&gt; 100% hypothesis longer than reference</span>
    </div>
  </div>

  {image_cards}

</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------

def _save_artifact(fixture_dir: Path, result: dict) -> Path:
    out_path = fixture_dir / f"eval_{result['commit']}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    return out_path


def _save_html(fixture_dir: Path, result: dict) -> Path:
    out_path = fixture_dir / f"eval_{result['commit']}.html"
    out_path.write_text(_render_html(result, fixture_dir), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate OCR against fixture ground truth")
    parser.add_argument(
        "--fixture",
        help="Run only this fixture subfolder name (default: all with ground_truth.txt)",
    )
    args = parser.parse_args(argv)

    from paddleocr import PaddleOCR
    import src.ocr_engine as engine_mod
    print("Initialising PaddleOCR (loading cached weights)…", file=sys.stderr)
    engine_mod._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    commit = _git_commit()

    if args.fixture:
        dirs = [FIXTURE_ROOT / args.fixture]
    else:
        dirs = sorted(
            d for d in FIXTURE_ROOT.iterdir()
            if d.is_dir() and (d / "ground_truth.txt").exists()
        )

    for fixture_dir in dirs:
        result = evaluate_fixture(fixture_dir, commit)
        _print_report(result)
        json_path = _save_artifact(fixture_dir, result)
        html_path = _save_html(fixture_dir, result)
        print(f"\nArtifacts saved →")
        print(f"  JSON : {json_path.relative_to(_PROJECT_ROOT)}")
        print(f"  HTML : {html_path.relative_to(_PROJECT_ROOT)}\n")


if __name__ == "__main__":
    main()
