"""
Logging setup for Docling GUI.

Configures Python's standard ``logging`` so that debugging is actually
possible after something goes wrong:

- A **rotating file on disk** (``config.LOG_FILE``) captures full detail: every
  user action, Docling's own internal logs, and complete tracebacks on errors.
  It survives restarts and crashes, so a bug report can start from the real
  history instead of "it broke".
- The in-window **Log tab** keeps showing clean, user-facing messages (no
  tracebacks), driven by the same logging system.

The file handler is attached to the *root* logger, so Docling's internal
logging flows into the same file for free. A few notoriously chatty third-party
loggers are capped so the file stays readable.

Usage:
    import logging_setup
    logging_setup.setup_file_logging()      # once, as early as possible
    logging_setup.log_session_header(...)    # environment banner (file only)
    logging_setup.attach_gui_handler(widget, root)  # once the Log tab exists

    from logging_setup import logger
    logger.info("user did a thing")
    logger.exception("it broke")             # full traceback -> file
"""
import contextlib
import logging
import logging.handlers
import platform
import sys
import tkinter as tk
from datetime import datetime

import config

# Application logger. All app code logs through this (or via DoclingGUI's
# log_message / log_error helpers, which forward to it).
logger = logging.getLogger("docling_gui")

# Full, machine-greppable format for the file.
_FILE_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
_FILE_DATEFMT = "%Y-%m-%d %H:%M:%S"

# Third-party loggers that emit huge volumes at DEBUG and drown out anything
# useful. Capped to WARNING so the file stays about *our* app and Docling.
_NOISY_LOGGERS = ("urllib3", "PIL", "matplotlib", "filelock", "fsspec",
                  "huggingface_hub", "datasets", "torch", "transformers")


class _GuiFilter(logging.Filter):
    """Keep the on-screen Log tab readable: show the app's own messages, plus
    any warnings/errors from elsewhere (e.g. Docling). Routine third-party
    INFO/DEBUG chatter still goes to the file, just not the window."""

    def filter(self, record):
        return (record.name.startswith("docling_gui")
                or record.levelno >= logging.WARNING)


class _GuiFormatter(logging.Formatter):
    """Render a record as ``[HH:MM:SS] message`` for the in-window Log tab.

    Errors/warnings get their level prefixed so they stand out. The full
    traceback is deliberately *not* included here (it goes to the file) to keep
    the on-screen log readable.
    """

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        message = record.getMessage()
        if record.levelno >= logging.WARNING:
            return f"[{timestamp}] {record.levelname}: {message}"
        return f"[{timestamp}] {message}"


class TkTextHandler(logging.Handler):
    """Logging handler that appends records to a Tk ``Text`` widget.

    ``emit`` can be called from any thread (the conversion runs on a worker
    thread), so the actual widget update is marshalled onto the Tk main loop
    via ``root.after``.
    """

    def __init__(self, text_widget, root):
        super().__init__()
        self.text_widget = text_widget
        self.root = root

    def emit(self, record):
        try:
            message = self.format(record)
        except Exception:  # pylint: disable=broad-except
            self.handleError(record)
            return
        # Schedule the widget write on the main thread; safe from any thread.
        # RuntimeError means the interpreter/main loop is shutting down.
        with contextlib.suppress(RuntimeError):
            self.root.after(0, self._append, message)

    def _append(self, message):
        try:
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, message + "\n")
            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)
        except tk.TclError:
            pass  # widget was destroyed during shutdown


def setup_file_logging():
    """Configure root + file logging. Idempotent. Returns the log file path."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Capture full detail from our own code and from Docling's internals.
    logger.setLevel(logging.DEBUG)
    logging.getLogger("docling").setLevel(logging.DEBUG)
    logging.getLogger("docling_core").setLevel(logging.DEBUG)
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Don't add a second file handler if called again.
    if any(getattr(h, "_docling_gui_file", False) for h in root_logger.handlers):
        return config.LOG_FILE

    try:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=1_000_000,   # ~1 MB per file
            backupCount=5,        # keep 5 rotated files
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(_FILE_FORMAT, datefmt=_FILE_DATEFMT))
        file_handler._docling_gui_file = True  # marker for the idempotency check
        root_logger.addHandler(file_handler)
    except OSError as exc:
        # Logging must never take the app down; fall back to console only.
        logging.getLogger(__name__).warning(
            "Could not open log file %s: %s", config.LOG_FILE, exc)

    return config.LOG_FILE


def attach_gui_handler(text_widget, root):
    """Route log records into the in-window Log tab. Call once, after the
    Log tab's Text widget exists."""
    handler = TkTextHandler(text_widget, root)
    handler.setLevel(logging.INFO)  # keep the on-screen log uncluttered
    handler.setFormatter(_GuiFormatter())
    handler.addFilter(_GuiFilter())
    logging.getLogger().addHandler(handler)
    return handler


def _docling_version(docling_available):
    """Best-effort installed Docling version string."""
    if not docling_available:
        return "NOT INSTALLED"
    try:
        from importlib.metadata import version
        return version("docling")
    except Exception:  # pylint: disable=broad-except
        return "unknown"


def log_session_header(dnd_available):
    """Log an environment banner. Call after setup_file_logging but before the
    GUI handler is attached, so it lands in the file only."""
    # Imported lazily so this logging module stays cheap to import on its own.
    import conversion_utils

    logger.info("=" * 60)
    logger.info("Docling GUI session started %s",
                datetime.now().isoformat(timespec="seconds"))
    logger.info("Platform : %s", platform.platform())
    logger.info("Python   : %s", sys.version.replace("\n", " "))
    logger.info("Docling  : %s", _docling_version(conversion_utils.DOCLING_AVAILABLE))
    logger.info("Pipelines: VLM=%s  ASR=%s  OCR-options=%s",
                conversion_utils.VLM_AVAILABLE,
                conversion_utils.ASR_AVAILABLE,
                conversion_utils.OCR_OPTIONS_AVAILABLE)
    logger.info("Drag&drop: %s", dnd_available)
    logger.info("Settings : %s", config.SETTINGS_FILE)
    logger.info("Log file : %s", config.LOG_FILE)
    logger.info("=" * 60)
