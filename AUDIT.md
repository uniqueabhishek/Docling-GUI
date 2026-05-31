# Codebase & Architecture Audit — Docling GUI

A Tkinter desktop front-end for IBM Docling (~880 LOC of application Python across
6 modules). This document records the audit findings and their resolution.

**Status: all findings implemented.** `ruff check .` is clean and the 12-test
`unittest` suite passes.

## Architecture

```
main.py              -> thin entry point, picks TkinterDnD vs tk.Tk
  docling_gui.py     -> DoclingGUI: controller, option state, conversion orchestration
  gui_panels.py      -> pure UI construction (panels/tabs/menu)
  conversion_utils.py-> docling adapter: build_converter / build_pipeline_options / export
  config.py          -> constants (extensions, languages, OCR engines, settings path)
  tooltip.py         -> standalone hover-tooltip widget
  tests/             -> unittest suite for conversion_utils
```

**Strengths**
- Clean module separation; every docling import is isolated behind `try/except` +
  `*_AVAILABLE` flags, so the GUI degrades gracefully when docling isn't installed.
- Threading done correctly: conversion runs on a daemon thread and **every** UI
  mutation is marshalled back to the main loop via `self.root.after(0, ...)`.
- Capability probing via `hasattr(...)` before setting optional pipeline fields
  keeps it resilient across docling versions.

## Findings & resolution

| # | Severity | Finding | Resolution | Commit |
|---|----------|---------|------------|--------|
| 1 | Critical | **VLM and ASR pipelines were completely broken.** `DocumentConverter(pipeline=...)` — no such parameter; an options *class* was passed instead of a configured pipeline. Selecting VLM/ASR raised `TypeError` and failed every file. The `vlm_model` selector was also never read. | Build both pipelines via `format_options={InputFormat.X: FormatOption(pipeline_cls=..., pipeline_options=...)}`. VLM registered for PDF + IMAGE, ASR for AUDIO, and `vlm_model` mapped to real docling model specs. Accelerator settings now passed in. | `5b7bee7` |
| 2 | High | **Non-PDF inputs ignored all options.** The Standard pipeline only registered `format_options` for `InputFormat.PDF`, so images ran with docling defaults (OCR/table/accelerator settings silently inert). | Register `ImageFormatOption` for `InputFormat.IMAGE` with the same options object as PDF. | `052fc01` |
| 3 | High | **`max_file_size_mb` was a dead option** — present in state but never surfaced in the UI or passed to `convert()`. | Added an Advanced-tab spinbox and wired it into `convert()` as `max_file_size` (MB -> bytes; 0 = unlimited). | `052fc01` |
| 4 | Medium | **OCR confidence slider was inert** for the default engine — `confidence_threshold` only applies to EasyOCR, not RapidOCR/Auto. | Slider is enabled only when EasyOCR is selected (wired to the engine dropdown, applied at startup and on reset), with a clarifying note and tooltip. | `052fc01` |
| 5 | Medium | **Default drift.** `build_pipeline_options` fallback defaults (`force_full_page_ocr=True`, `ocr_confidence=0.8`, `device='cpu'`) contradicted the GUI defaults — a trap for any partial settings dict. | Aligned the fallbacks with the GUI defaults (`False`, `0.5`, `'auto'`). | `27ad829` |
| 6 | Medium | **Picture description ignored the `vlm_model` selector** — it always used docling's default description model. | When picture description is enabled, select the granite or smolvlm description preset to match `vlm_model`, guarded for older docling versions. | `0c2fde4` |
| 7 | Low | **`OcrMac` was supported in code but unreachable** — never listed in the engine dropdown. | Centralised the engine list in `config.OCR_ENGINES` (platform-aware) so OcrMac appears only on macOS; documented in the tooltip. | `baa1a61` |
| 8 | Low | **No settings persistence** between launches; "Set Default Output Directory" didn't actually persist. | Save options to `~/.docling_gui_settings.json` on close, restore on launch, and sync dependent widget states. The chosen output directory now sticks. | `03c58ee` |
| 9 | Low | **God-class / triple-maintained option list.** `init_variables`, `get_current_settings` and `reset_options` each repeated the same ~30 keys, risking silent desync. | Defined names + defaults once in `OPTION_DEFAULTS`, inferred each tk variable type from its default, and reduced the three methods to loops. Class-level annotations preserve static type info. | `930898b` |
| 10 | Low | **No tests / no safety net** — the critical bug lived in pure, testable functions. | Added a stdlib `unittest` suite (no new dependencies) covering output extensions, content export (incl. Text markdown-stripping), and converter/pipeline construction. The VLM/ASR cases guard the construction regression. | `27ad829`, `0c2fde4` |

## Verification

- `ruff check .` — clean.
- `python -m unittest discover -s tests` — 12 tests, all passing.
- Headless GUI build, settings round-trip, and refactor-equivalence checks all pass.

## Notes / deferred (non-code)

- **Mid-file cancellation** is still coarse — `cancel_requested` is checked between
  files, not within a single long conversion. `document_timeout` is the escape hatch.
  Deferred as an architectural change rather than a defect.
- **`UI Improvements.md`** is a scratch document tracked in the repo; keep-or-remove
  is a maintainer decision, not a code fix.
