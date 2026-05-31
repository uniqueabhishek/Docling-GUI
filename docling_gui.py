"""
Docling GUI - A full-featured GUI for IBM Docling document conversion
Supports all Docling features including OCR, VLM, ASR pipelines
"""

import contextlib
import json
import os
import subprocess
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

# Import refactored modules
import config
import gui_panels
from conversion_utils import (
    DOCLING_AVAILABLE,
    build_converter,
    export_content,
    get_output_extension,
)

# Try to import drag-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    DND_FILES = None


# Single source of truth for every option variable: name -> default value.
# The tk variable type is inferred from the default (bool -> BooleanVar,
# int -> IntVar, float -> DoubleVar, str -> StringVar). A callable default is
# evaluated at init/reset time (used for the home-relative output directory).
OPTION_DEFAULTS: dict[str, Any] = {
    # Basic
    "pipeline_type": "Standard",
    "vlm_model": "granite_docling",
    "output_format": "Markdown",
    # Feature toggles
    "enable_ocr": True,
    "do_table_structure": True,
    "generate_picture_images": False,
    "do_formula_enrichment": True,
    "do_code_enrichment": True,
    "do_picture_classification": True,
    "do_picture_description": False,
    # OCR
    "ocr_engine": "RapidOCR",
    "ocr_language": "en",
    "force_full_page_ocr": False,
    "ocr_confidence": 0.5,
    # Table
    "table_mode": "Accurate",
    "do_cell_matching": True,
    # Advanced
    "max_pages": 0,
    "max_file_size_mb": 0,
    "document_timeout": 0,
    "generate_page_images": False,
    "generate_table_images": False,
    "images_scale": 1.0,
    # Accelerator
    "device": "auto",
    "num_threads": 4,
    "use_flash_attention": False,
    # Output
    "output_directory": lambda: str(Path.home() / "Documents"),
    "create_subfolder": False,
    "overwrite_files": False,
}


def _resolve_default(default):
    """Evaluate a callable default, otherwise return it unchanged."""
    return default() if callable(default) else default


def _make_var(default):
    """Create the appropriate tk variable for a resolved default value."""
    # bool must be checked before int, since bool is a subclass of int.
    if isinstance(default, bool):
        return tk.BooleanVar(value=default)
    if isinstance(default, int):
        return tk.IntVar(value=default)
    if isinstance(default, float):
        return tk.DoubleVar(value=default)
    return tk.StringVar(value=str(default))


class DoclingGUI:
    """
    Main GUI class for Docling Document Converter.
    Handles UI creation, option management, and conversion process.
    """

    # Option variables are created dynamically in init_variables from
    # OPTION_DEFAULTS; declared here so static type checkers know they exist.
    pipeline_type: tk.StringVar
    vlm_model: tk.StringVar
    output_format: tk.StringVar
    enable_ocr: tk.BooleanVar
    do_table_structure: tk.BooleanVar
    generate_picture_images: tk.BooleanVar
    do_formula_enrichment: tk.BooleanVar
    do_code_enrichment: tk.BooleanVar
    do_picture_classification: tk.BooleanVar
    do_picture_description: tk.BooleanVar
    ocr_engine: tk.StringVar
    ocr_language: tk.StringVar
    force_full_page_ocr: tk.BooleanVar
    ocr_confidence: tk.DoubleVar
    table_mode: tk.StringVar
    do_cell_matching: tk.BooleanVar
    max_pages: tk.IntVar
    max_file_size_mb: tk.IntVar
    document_timeout: tk.IntVar
    generate_page_images: tk.BooleanVar
    generate_table_images: tk.BooleanVar
    images_scale: tk.DoubleVar
    device: tk.StringVar
    num_threads: tk.IntVar
    use_flash_attention: tk.BooleanVar
    output_directory: tk.StringVar
    create_subfolder: tk.BooleanVar
    overwrite_files: tk.BooleanVar

    def __init__(self, root):
        self.root = root
        self.root.title("Docling GUI - Full-Featured Document Converter")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)

        # Setup modern theme and styling
        self.setup_theme()

        # File list storage
        self.file_list = []

        # Conversion state
        self.is_converting = False
        self.cancel_requested = False
        self.converter: Any = None

        # UI Components (created by gui_panels during layout construction)
        self.file_listbox: tk.Listbox
        self.context_menu: tk.Menu
        self.file_count_label: ttk.Label
        self.options_notebook: ttk.Notebook
        self.vlm_frame: ttk.Frame
        self.conf_label: ttk.Label
        self.conf_scale: ttk.Scale
        self.preview_notebook: ttk.Notebook
        self.preview_text: tk.Text
        self.log_text: tk.Text
        self.progress_var: tk.DoubleVar
        self.progress_bar: ttk.Progressbar
        self.progress_label: ttk.Label
        self.status_label: ttk.Label
        self.convert_selected_btn: tk.Button
        self.convert_all_btn: tk.Button
        self.cancel_btn: tk.Button

        # Initialize all option variables
        self.init_variables()

        # Build the UI
        gui_panels.create_menu(self)
        self.create_main_layout()

        # Setup drag and drop if available
        self.setup_drag_drop()

        # Restore previously saved settings and persist on close
        self.load_settings()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Check if docling is available
        if not DOCLING_AVAILABLE:
            self.log_message(
                "WARNING: Docling is not installed. Please run: pip install docling")

    def setup_theme(self):
        """Setup modern theme and custom styling"""
        style = ttk.Style()

        # Use modern theme based on platform
        available_themes = style.theme_names()
        if 'vista' in available_themes:  # Windows
            style.theme_use('vista')
        elif 'aqua' in available_themes:  # macOS
            style.theme_use('aqua')
        elif 'clam' in available_themes:  # Cross-platform modern
            style.theme_use('clam')

        # Note: Custom button colors are applied via tk.Button (not ttk)
        # because the Windows vista theme ignores ttk background/foreground.

        # Enhanced progress bar
        style.configure(
            'Horizontal.TProgressbar',
            troughcolor='#e5e7eb',
            background='#2563eb',
            thickness=20
        )

        # Notebook (tabs) styling
        style.configure(
            'TNotebook.Tab',
            padding=[12, 8],
            font=('', 9)
        )
        style.map(
            'TNotebook.Tab',
            foreground=[('selected', '#2563eb')]
        )

        # LabelFrame styling
        style.configure(
            'TLabelframe',
            borderwidth=2,
            relief='solid'
        )
        style.configure(
            'TLabelframe.Label',
            font=('', 10, 'bold'),
            foreground='#1f2937'
        )

    def init_variables(self):
        """Create every option variable from OPTION_DEFAULTS."""
        for name, default in OPTION_DEFAULTS.items():
            setattr(self, name, _make_var(_resolve_default(default)))

    def get_current_settings(self):
        """Collect current settings into a dictionary"""
        return {name: getattr(self, name).get() for name in OPTION_DEFAULTS}

    def create_main_layout(self):
        """Create the main window layout"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top section: Input and Options side by side (fixed height)
        top_frame = ttk.Frame(main_frame, height=300)
        top_frame.pack(fill=tk.BOTH)
        top_frame.pack_propagate(False)

        # Configure grid weights
        top_frame.columnconfigure(0, weight=2)
        top_frame.columnconfigure(1, weight=3)
        top_frame.rowconfigure(0, weight=1)

        # Create panels using extracted module
        gui_panels.create_input_panel(self, top_frame)
        gui_panels.create_options_panel(self, top_frame)

        # Output settings
        gui_panels.create_output_panel(self, main_frame)

        # Progress and controls (pack before preview so buttons are always visible)
        gui_panels.create_controls_panel(self, main_frame)

        # Preview/Log panel (expands to fill remaining space)
        gui_panels.create_preview_panel(self, main_frame)

    # ==================== Event Handlers ====================

    def on_pipeline_change(self, _=None):
        """Handle pipeline type change"""
        pipeline = self.pipeline_type.get()
        if pipeline == "VLM":
            self.vlm_frame.pack(side=tk.LEFT)
        else:
            self.vlm_frame.pack_forget()

    def on_ocr_engine_change(self, _=None):
        """Enable the confidence slider only for EasyOCR (the only engine
        that honours it); disable it for RapidOCR/Auto."""
        state = tk.NORMAL if self.ocr_engine.get() == "EasyOCR" else tk.DISABLED
        self.conf_scale.config(state=state)

    def reset_options(self):
        """Reset all options to defaults by updating existing variables"""
        for name, default in OPTION_DEFAULTS.items():
            getattr(self, name).set(_resolve_default(default))

        # Hide VLM frame if shown
        self.vlm_frame.pack_forget()

        # Refresh dependent widget states (e.g. confidence slider)
        self.on_ocr_engine_change()

        messagebox.showinfo(
            "Reset", "All options have been reset to defaults.")

    # ==================== File Operations ====================

    def add_files(self):
        """Open file dialog to add files"""
        filetypes = [
            ("All Supported", " ".join(
                f"*{ext}" for ext in config.SUPPORTED_EXTENSIONS)),
            ("PDF Files", "*.pdf"),
            ("Word Documents", "*.docx"),
            ("PowerPoint", "*.pptx"),
            ("Excel", "*.xlsx"),
            ("HTML Files", "*.html *.htm"),
            ("Images", "*.png *.jpg *.jpeg *.tiff *.tif *.bmp"),
            ("Audio Files", "*.wav *.mp3"),
            ("All Files", "*.*")
        ]

        files = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=filetypes
        )

        for file in files:
            self.add_file_to_list(file)

    def add_folder(self):
        """Add all supported files from a folder"""
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            count = 0
            for root, _, files in os.walk(folder):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in config.SUPPORTED_EXTENSIONS:
                        self.add_file_to_list(os.path.join(root, file))
                        count += 1
            self.log_message(f"Added {count} files from folder")

    def add_file_to_list(self, filepath):
        """Add a single file to the list. Returns True if added."""
        if filepath not in self.file_list:
            ext = os.path.splitext(filepath)[1].lower()
            if ext in config.SUPPORTED_EXTENSIONS:
                self.file_list.append(filepath)
                display_name = os.path.basename(filepath)
                self.file_listbox.insert(tk.END, display_name)
                self.update_file_count()
                return True
            else:
                self.log_message(f"Unsupported file type: {filepath}")
        return False

    def remove_selected(self):
        """Remove selected files from the list"""
        selection = self.file_listbox.curselection()
        for index in reversed(selection):
            self.file_listbox.delete(index)
            del self.file_list[index]
        self.update_file_count()

    def clear_files(self):
        """Clear all files from the list"""
        self.file_listbox.delete(0, tk.END)
        self.file_list.clear()
        self.update_file_count()

    def update_file_count(self):
        """Update the file count label"""
        count = len(self.file_list)
        self.file_count_label.config(
            text=f"{count} file{'s' if count != 1 else ''}")

    def on_file_select(self, _):
        """Handle file selection for preview"""
        try:
            selection = self.file_listbox.curselection()
            if selection:
                index = selection[0]
                if index < len(self.file_list):
                    filepath = self.file_list[index]
                    self.show_file_info(filepath)
        except Exception as e:  # pylint: disable=broad-except
            self.log_message(f"Selection error: {e}")

    def show_file_info(self, filepath):
        """Show file info in preview panel"""
        try:
            if not os.path.exists(filepath):
                self.log_message(f"File not found: {filepath}")
                return

            stat = os.stat(filepath)
            size = stat.st_size
            if size < 1024:
                size_str = f"{size} bytes"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            ext = os.path.splitext(filepath)[1].lower()
            info = f"File: {os.path.basename(filepath)}\n"
            info += f"Path: {filepath}\n"
            info += f"Size: {size_str}\n"
            info += f"Type: {config.SUPPORTED_EXTENSIONS.get(ext, 'Unknown')}\n"

            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, info)
            self.preview_text.config(state=tk.DISABLED)

            # Switch to preview tab if not already there
            self.preview_notebook.select(0)

        except Exception as e:  # pylint: disable=broad-except
            self.log_message(f"Error reading file info: {e}")

            # Show error in preview window as well
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, f"Error reading file info: {e}")
            self.preview_text.config(state=tk.DISABLED)

    def show_context_menu(self, event):
        """Show right-click context menu"""
        try:
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(
                self.file_listbox.nearest(event.y))
            self.file_listbox.activate(self.file_listbox.nearest(event.y))
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def open_in_explorer(self):
        """Open selected file location in Explorer/Finder"""
        selection = self.file_listbox.curselection()
        if selection:
            folder = os.path.dirname(self.file_list[selection[0]])
            if os.name == 'nt':
                os.startfile(folder)
            elif os.name == 'posix':
                subprocess.run(['open', folder], check=False)

    def browse_output_dir(self):
        """Browse for output directory"""
        folder = filedialog.askdirectory(title="Select Output Directory")
        if folder:
            self.output_directory.set(folder)

    def set_default_output(self):
        """Set default output directory"""
        self.browse_output_dir()

    # ==================== Drag and Drop Support ====================

    def setup_drag_drop(self):
        """Setup drag and drop support for file listbox"""
        if not DND_AVAILABLE:
            self.log_message(
                "Drag & Drop not available. Install tkinterdnd2 for this feature.")
            return

        try:
            # tkinterdnd2 adds these methods at runtime via a mixin; the base
            # Listbox stub doesn't know about them, so access through Any.
            listbox: Any = self.file_listbox

            # Register the listbox as a drop target
            listbox.drop_target_register(DND_FILES)
            listbox.dnd_bind('<<Drop>>', self.on_drop)

            # Add visual feedback on drag over
            listbox.dnd_bind('<<DragEnter>>', self.on_drag_enter)
            listbox.dnd_bind('<<DragLeave>>', self.on_drag_leave)

            self.log_message(
                "Drag & Drop enabled - Drop files or folders here!")
        except Exception as e:  # pylint: disable=broad-except
            self.log_message(f"Could not enable drag & drop: {e}")

    def on_drag_enter(self, _event):
        """Visual feedback when dragging over the listbox"""
        self.file_listbox.config(background='#e8f4f8')

    def on_drag_leave(self, _event):
        """Remove visual feedback when drag leaves"""
        self.file_listbox.config(background='white')

    def on_drop(self, event):
        """Handle dropped files and folders"""
        # Remove visual feedback
        self.file_listbox.config(background='white')

        # Get dropped files/folders
        files = self.root.tk.splitlist(event.data)

        added_count = 0
        for item in files:
            # Clean up the path (remove curly braces if present)
            item = item.strip('{}')

            if os.path.isfile(item):
                if self.add_file_to_list(item):
                    added_count += 1
            elif os.path.isdir(item):
                for root, _, dir_files in os.walk(item):
                    for file in dir_files:
                        if self.add_file_to_list(os.path.join(root, file)):
                            added_count += 1

        if added_count > 0:
            self.log_message(f"Added {added_count} file(s) via drag & drop")
        else:
            self.log_message("No supported files found in dropped items")

    # ==================== Conversion Logic ====================

    def convert_selected(self):
        """Convert only selected files"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "No Selection", "Please select files to convert.")
            return

        files = [self.file_list[i] for i in selection]
        self.start_conversion(files)

    def convert_all(self):
        """Convert all files in the list"""
        if not self.file_list:
            messagebox.showwarning("No Files", "Please add files to convert.")
            return

        self.start_conversion(self.file_list.copy())

    def start_conversion(self, files):
        """Start the conversion process in a separate thread"""
        if not DOCLING_AVAILABLE:
            messagebox.showerror("Docling Not Installed",
                                 "Docling is not installed. Please run:\npip install docling")
            return

        if self.is_converting:
            return

        self.is_converting = True
        self.cancel_requested = False

        # Update UI state
        self.convert_selected_btn.config(state=tk.DISABLED)
        self.convert_all_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)

        # Switch to log tab
        self.preview_notebook.select(1)

        # Gets current settings to pass to thread
        settings = self.get_current_settings()

        # Start conversion thread
        thread = threading.Thread(
            target=self.conversion_worker, args=(files, settings))
        thread.daemon = True
        thread.start()

    def conversion_worker(self, files, settings):
        """Worker thread for conversion"""
        try:
            # Log configuration
            self.log_message("=== Conversion Configuration ===")
            self.log_message(f"Pipeline: {settings['pipeline_type']}")
            self.log_message(f"Output Format: {settings['output_format']}")
            self.log_message(
                f"OCR: {settings['enable_ocr']}, Engine: {settings['ocr_engine']}, "
                f"Lang: {settings['ocr_language']}"
            )
            self.log_message(f"Table Mode: {settings['table_mode']}")
            self.log_message(
                f"Device: {settings['device']}, Threads: {settings['num_threads']}")
            self.log_message("================================")

            # Build converter with proper pipeline type
            self.converter, pipeline_name = build_converter(settings)
            self.log_message(f"Using {pipeline_name} pipeline")

            total = len(files)
            successful = 0
            failed = 0

            for i, filepath in enumerate(files):
                if self.cancel_requested:
                    self.log_message("Conversion cancelled by user")
                    break

                filename = os.path.basename(filepath)
                self.update_status(f"Converting: {filename}")
                self.log_message(f"Converting: {filename}")

                try:
                    # Apply page limit (first N pages) if set; 0 = all pages
                    convert_kwargs = {}
                    max_pages = settings.get('max_pages', 0)
                    if max_pages and max_pages > 0:
                        convert_kwargs['page_range'] = (1, max_pages)

                    # Apply max file size limit (MB -> bytes); 0 = unlimited
                    max_file_size_mb = settings.get('max_file_size_mb', 0)
                    if max_file_size_mb and max_file_size_mb > 0:
                        convert_kwargs['max_file_size'] = max_file_size_mb * 1024 * 1024

                    # Convert the document
                    result = self.converter.convert(filepath, **convert_kwargs)

                    # Export based on selected format
                    output_format = settings['output_format']
                    output_ext = get_output_extension(output_format)

                    # Determine output path
                    base_name = os.path.splitext(filename)[0]
                    output_dir = settings['output_directory']

                    if settings['create_subfolder']:
                        output_dir = os.path.join(output_dir, base_name)

                    os.makedirs(output_dir, exist_ok=True)

                    output_path = os.path.join(
                        output_dir, f"{base_name}{output_ext}")

                    # Check for overwrite
                    if os.path.exists(output_path) and not settings['overwrite_files']:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_path = os.path.join(
                            output_dir, f"{base_name}_{timestamp}{output_ext}"
                        )

                    # Export content
                    content = export_content(result, output_format)

                    # Write to file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    self.log_message(f"  Saved: {output_path}")
                    successful += 1

                    # Update preview with last converted content
                    self.update_preview(content[:5000])  # Limit preview size

                except Exception as e:  # pylint: disable=broad-except
                    self.log_message(f"  ERROR: {str(e)}")
                    failed += 1

                # Update progress
                progress = ((i + 1) / total) * 100
                self.update_progress(progress)

            # Final summary
            self.log_message("\n=== Conversion Complete ===")
            self.log_message(f"Successful: {successful}")
            self.log_message(f"Failed: {failed}")
            self.log_message("===========================")

        except Exception as e:  # pylint: disable=broad-except
            self.log_message(f"Conversion error: {str(e)}")

        finally:
            self.is_converting = False
            self.root.after(0, self.conversion_finished)

    def cancel_conversion(self):
        """Cancel the ongoing conversion"""
        self.cancel_requested = True
        self.update_status("Cancelling...")

    def conversion_finished(self):
        """Called when conversion is complete"""
        self.convert_selected_btn.config(state=tk.NORMAL)
        self.convert_all_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.update_status("Ready")

    # ==================== UI Updates ====================

    def update_progress(self, value):
        """Update progress bar (thread-safe)"""
        self.root.after(0, lambda: self._update_progress(value))

    def _update_progress(self, value):
        self.progress_var.set(value)
        self.progress_label.config(text=f"{int(value)}%")

    def update_status(self, text):
        """Update status label (thread-safe)"""
        self.root.after(0, lambda: self.status_label.config(text=text))

    def log_message(self, message):
        """Add message to log (thread-safe)"""
        self.root.after(0, lambda: self._log_message(message))

    def _log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_preview(self, content):
        """Update preview panel (thread-safe)"""
        self.root.after(0, lambda: self._update_preview(content))

    def _update_preview(self, content):
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, content)
        self.preview_text.config(state=tk.DISABLED)

    # ==================== Menu Actions ====================

    def open_docs(self):
        """Open Docling documentation in browser"""
        webbrowser.open("https://docling-project.github.io/docling/")

    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About Docling GUI", config.ABOUT_TEXT)

    # ==================== Settings Persistence ====================

    def apply_settings(self, data):
        """Apply a saved settings dict onto the option variables.

        Setting names match the variable attribute names, so each key maps
        directly to a tk.Variable on this instance.
        """
        for key, value in data.items():
            var = getattr(self, key, None)
            if isinstance(var, tk.Variable):
                # Ignore stale/invalid values from an older settings file.
                with contextlib.suppress(tk.TclError, ValueError):
                    var.set(value)

    def load_settings(self):
        """Load persisted settings from disk, if present."""
        try:
            if config.SETTINGS_FILE.exists():
                with open(config.SETTINGS_FILE, encoding='utf-8') as f:
                    data = json.load(f)
                self.apply_settings(data)
                # Sync dependent widget states to the restored values.
                self.on_pipeline_change()
                self.on_ocr_engine_change()
        except (OSError, json.JSONDecodeError) as e:
            self.log_message(f"Could not load saved settings: {e}")

    def save_settings(self):
        """Persist the current settings to disk."""
        try:
            with open(config.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.get_current_settings(), f, indent=2)
        except OSError as e:
            self.log_message(f"Could not save settings: {e}")

    def on_close(self):
        """Save settings and close the window."""
        self.save_settings()
        self.root.destroy()


def main():
    """Main entry point"""
    # Use TkinterDnD if available for drag-drop support
    root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk()

    DoclingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
