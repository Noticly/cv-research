# Skill: ocr-eval

## Purpose

Commit any pending source changes, then run the OCR fixture evaluation so that
every eval artifact (JSON + HTML) contains the git commit that is being tested.

## When to invoke

Use this skill when the user says any of:
- "run the eval" / "run eval"
- "run the OCR eval"
- "run tests" / "run the fixture tests"
- `/ocr-eval`
- `/ocr-eval <fixture-name>` (e.g. `/ocr-eval medicine_package`)

The optional argument after the skill name is the fixture subfolder to target.
If omitted, all fixtures that have a `ground_truth.txt` are evaluated.

## Steps

### 1. Identify uncommitted source changes

```bash
git -C /home/xyu/Projects/OpenClarity status --short
```

Classify files:
- **Source files** — anything under `research/OCR/src/` or `research/OCR/test/`
  that is not an eval artifact (`eval_*.json`, `eval_*.html`)
- **Ground truth files** — `research/OCR/test/fixtures/**/ground_truth.txt`
- **Eval artifacts** — `eval_*.json` and `eval_*.html` inside fixture folders;
  these are outputs of a prior run and should NOT be committed before the eval

### 2. Commit source and ground truth changes (if any)

If there are uncommitted source or ground truth changes:

a. Stage only those files:
```bash
git -C /home/xyu/Projects/OpenClarity add <source and ground_truth files only>
```

b. Draft a commit message:
- Look at `git diff --cached` for what changed.
- Write a concise subject line (≤ 72 chars) that describes the change.
- Do NOT include eval artifacts in this commit.

c. Commit:
```bash
git -C /home/xyu/Projects/OpenClarity commit -m "$(cat <<'EOF'
<subject line>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

If there are no source changes (only eval artifacts pending, or nothing at all),
skip the commit step — the HEAD commit is already the relevant one.

### 3. Run the evaluation

From `research/OCR/`:
```bash
/usr/bin/python3.10 test/eval_fixtures.py [--fixture <fixture-name>]
```

Use `--fixture <name>` only when the user specified a fixture. Otherwise omit
the flag to run all fixtures.

Always capture stderr separately (redirect `2>/dev/null`) — it contains
PaddleOCR progress noise that clutters the output.

### 4. Stage and commit eval artifacts

After the eval run, stage the newly written artifact files:
```bash
git -C /home/xyu/Projects/OpenClarity add research/OCR/test/fixtures/**/eval_*.json \
    research/OCR/test/fixtures/**/eval_*.html
```

Commit them with a message that references the source commit and fixture:
```bash
git -C /home/xyu/Projects/OpenClarity commit -m "$(cat <<'EOF'
[OCR eval] <fixture-name or "all fixtures"> — <hash of source commit>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### 5. Report results

Print a concise summary to the user:
- Which commit was under test (hash + subject)
- Per-fixture verdict (PASS / NEEDS IMPROVEMENT) and mean score
- Per-image key-phrase recall or CER with ✓/✗ status
- Paths to the generated HTML reports

Highlight any regressions compared to the previous run if visible in the stdout
output from step 3.

## Conventions

- Always commit source before eval so the artifact's embedded commit hash refers
  to the code being tested, not a prior or later commit.
- Never include eval artifacts in the source commit; they belong in their own
  follow-up commit so `git log` clearly separates "what changed" from "what the
  eval saw."
- The Python interpreter is `/usr/bin/python3.10` (system interpreter with
  paddleocr installed); do not use the venv interpreter at
  `research/ObjectDetection/.venv/bin/python3`.
- Working directory for the eval command is `research/OCR/` (the script uses
  relative imports via `sys.path.insert`).
