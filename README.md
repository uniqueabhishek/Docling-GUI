# Docling GUI

A full-featured graphical interface for [IBM Docling](https://github.com/docling-project/docling), allowing easy document conversion to Markdown, HTML, JSON, and more.

## Features

*   **User-Friendly Interface**: Easy-to-use GUI built with Tkinter.
*   **Multiple Formats**: Convert PDF, DOCX, PPTX, XLSX, HTML, Images, and Audio.
*   **OCR Support**: Built-in OCR via RapidOCR (default; used by the "Auto" setting). EasyOCR is also supported but must be installed separately.
*   **Advanced Options**: Configure table extraction, image generation, and hardware acceleration (CPU/GPU).
*   **Batch Processing**: Convert single files or entire folders.
*   **Preview**: View file details and conversion preview directly in the app.

## Requirements

*   Python 3.10+

## Installation

This project uses `uv` for dependency management.

1.  **Install `uv`** (if not installed):
    ```bash
    pip install uv
    ```

2.  **Install Dependencies**:
    ```bash
    uv sync
    ```

## Usage

Run the application:
```bash
uv run main.py
```
Or if using standard python:
```bash
python main.py
```

## Configuration

Settings are adjustable via the GUI tabs:
*   **Basic**: Output format, pipeline type (Standard, VLM, ASR).
*   **OCR**: Engine selection, language, confidence threshold.
*   **Advanced**: Page limits, timeouts, image scaling.
*   **Accelerator**: CPU threads, GPU selection (CUDA/MPS).
