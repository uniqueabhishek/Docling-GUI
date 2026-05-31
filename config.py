"""
Configuration and constants for Docling GUI
"""
import sys
from pathlib import Path

# Location of the persisted user settings (saved on close, loaded on launch).
SETTINGS_FILE = Path.home() / ".docling_gui_settings.json"

# Location of the persistent, rotating debug log. Captures full detail (user
# actions, Docling's own internal logs, and complete tracebacks) so problems
# can be diagnosed after the fact. Lives next to the settings file.
LOG_DIR = Path.home() / ".docling_gui_logs"
LOG_FILE = LOG_DIR / "docling_gui.log"

# OCR engines offered in the UI. OcrMac relies on Apple's Vision framework
# and is only usable on macOS, so it is hidden on other platforms.
OCR_ENGINES = ["Auto", "RapidOCR", "EasyOCR"]
if sys.platform == "darwin":
    OCR_ENGINES.append("OcrMac")

# Supported file extensions (including audio for ASR)
SUPPORTED_EXTENSIONS = {
    '.pdf': 'PDF Documents',
    '.docx': 'Word Documents',
    '.pptx': 'PowerPoint Presentations',
    '.xlsx': 'Excel Spreadsheets',
    '.html': 'HTML Files',
    '.htm': 'HTML Files',
    '.png': 'PNG Images',
    '.jpg': 'JPEG Images',
    '.jpeg': 'JPEG Images',
    '.tiff': 'TIFF Images',
    '.tif': 'TIFF Images',
    '.bmp': 'BMP Images',
    '.wav': 'WAV Audio',
    '.mp3': 'MP3 Audio',
    '.vtt': 'WebVTT Subtitles',
}

# OCR Languages
OCR_LANGUAGES = [
    ('en', 'English'),
    ('de', 'German'),
    ('fr', 'French'),
    ('es', 'Spanish'),
    ('it', 'Italian'),
    ('pt', 'Portuguese'),
    ('nl', 'Dutch'),
    ('pl', 'Polish'),
    ('ru', 'Russian'),
    ('zh', 'Chinese'),
    ('ja', 'Japanese'),
    ('ko', 'Korean'),
    ('ar', 'Arabic'),
    ('hi', 'Hindi'),
    ('th', 'Thai'),
    ('vi', 'Vietnamese'),
    ('tr', 'Turkish'),
    ('el', 'Greek'),
    ('he', 'Hebrew'),
    ('uk', 'Ukrainian'),
]

ABOUT_TEXT = """Docling GUI - Full-Featured Document Converter

A comprehensive graphical interface for IBM Docling.

FEATURES:
- Multiple input formats: PDF, DOCX, PPTX, XLSX, HTML, Images, Audio
- Multiple output formats: Markdown, HTML, JSON, DocTags, Text
- Pipeline types: Standard, VLM (Vision Language Model), ASR (Speech)
- OCR engines: Auto, RapidOCR (Default/Built-in), EasyOCR (separate install)
- Table extraction: Fast and Accurate modes
- Formula and code enrichment
- Picture classification and description
- GPU acceleration (CUDA, MPS)
- Batch processing with progress tracking

https://github.com/docling-project/docling
https://docling-project.github.io/docling/
"""
