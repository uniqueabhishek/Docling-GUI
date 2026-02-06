"""
Docling GUI - A full-featured GUI for IBM Docling document conversion
Supports all Docling features including OCR, VLM, ASR pipelines
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import os
import webbrowser
from pathlib import Path
from datetime import datetime

# Import refactored modules
import config
import gui_panels
from conversion_utils import (
    DOCLING_AVAILABLE,
    get_output_extension,
    export_content,
    build_converter,
)

# Try to import drag-drop support
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    DND_FILES = None


class DoclingGUI:
    """
    Main GUI class for Docling Document Converter.
    Handles UI creation, option management, and conversion process.
    """

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
        self.converter = None

        # UI Components initialized to None
        self.file_listbox = None
        self.context_menu = None
        self.file_count_label = None
        self.options_notebook = None
        self.vlm_frame = None
        self.conf_label = None
        self.preview_notebook = None
        self.preview_text = None
        self.log_text = None
        self.progress_var = None
        self.progress_bar = None
        self.progress_label = None
        self.status_label = None
        self.convert_selected_btn = None
        self.convert_all_btn = None
        self.cancel_btn = None

        # Initialize all option variables
        self.init_variables()

        # Build the UI
        gui_panels.create_menu(self)
        self.create_main_layout()

        # Setup drag and drop if available
        self.setup_drag_drop()

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
        """Initialize all option variables"""
        # Basic Options
        self.pipeline_type = tk.StringVar(value="Standard")
        self.vlm_model = tk.StringVar(value="granite_docling")
        self.output_format = tk.StringVar(value="Markdown")

        # Feature toggles
        self.enable_ocr = tk.BooleanVar(value=True)
        self.do_table_structure = tk.BooleanVar(value=True)
        self.generate_picture_images = tk.BooleanVar(value=False)
        self.do_formula_enrichment = tk.BooleanVar(value=True)
        self.do_code_enrichment = tk.BooleanVar(value=True)
        self.do_picture_classification = tk.BooleanVar(value=True)
        self.do_picture_description = tk.BooleanVar(value=False)

        # OCR Options
        self.ocr_engine = tk.StringVar(value="RapidOCR")
        self.ocr_language = tk.StringVar(value="en")
        self.force_full_page_ocr = tk.BooleanVar(value=False)
        self.ocr_confidence = tk.DoubleVar(value=0.5)

        # Table Options
        self.table_mode = tk.StringVar(value="Accurate")
        self.do_cell_matching = tk.BooleanVar(value=True)

        # Advanced Options
        self.max_pages = tk.IntVar(value=0)
        self.max_file_size_mb = tk.IntVar(value=0)
        self.document_timeout = tk.IntVar(value=0)
        self.generate_page_images = tk.BooleanVar(value=False)
        self.generate_table_images = tk.BooleanVar(value=False)
        self.images_scale = tk.DoubleVar(value=1.0)

        # Accelerator Options
        self.device = tk.StringVar(value="auto")
        self.num_threads = tk.IntVar(value=4)
        self.use_flash_attention = tk.BooleanVar(value=False)

        # Output Options
        self.output_directory = tk.StringVar(
            value=str(Path.home() / "Documents"))
        self.create_subfolder = tk.BooleanVar(value=False)
        self.overwrite_files = tk.BooleanVar(value=False)

    def get_current_settings(self):
        """Collect current settings into a dictionary"""
        return {
            'pipeline_type': self.pipeline_type.get(),
            'vlm_model': self.vlm_model.get(),
            'output_format': self.output_format.get(),

            'enable_ocr': self.enable_ocr.get(),
            'do_table_structure': self.do_table_structure.get(),
            'generate_picture_images': self.generate_picture_images.get(),
            'do_formula_enrichment': self.do_formula_enrichment.get(),
            'do_code_enrichment': self.do_code_enrichment.get(),
            'do_picture_classification': self.do_picture_classification.get(),
            'do_picture_description': self.do_picture_description.get(),

            'ocr_engine': self.ocr_engine.get(),
            'ocr_language': self.ocr_language.get(),
            'force_full_page_ocr': self.force_full_page_ocr.get(),
            'ocr_confidence': self.ocr_confidence.get(),

            'table_mode': self.table_mode.get(),
            'do_cell_matching': self.do_cell_matching.get(),

            'max_pages': self.max_pages.get(),
            'max_file_size_mb': self.max_file_size_mb.get(),
            'document_timeout': self.document_timeout.get(),
            'generate_page_images': self.generate_page_images.get(),
            'generate_table_images': self.generate_table_images.get(),
            'images_scale': self.images_scale.get(),

            'device': self.device.get(),
            'num_threads': self.num_threads.get(),
            'use_flash_attention': self.use_flash_attention.get(),

            'output_directory': self.output_directory.get(),
            'create_subfolder': self.create_subfolder.get(),
            'overwrite_files': self.overwrite_files.get(),
        }

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

    def reset_options(self):
        """Reset all options to defaults by updating existing variables"""
        self.pipeline_type.set("Standard")
        self.vlm_model.set("granite_docling")
        self.output_format.set("Markdown")

        self.enable_ocr.set(True)
        self.do_table_structure.set(True)
        self.generate_picture_images.set(False)
        self.do_formula_enrichment.set(True)
        self.do_code_enrichment.set(True)
        self.do_picture_classification.set(True)
        self.do_picture_description.set(False)

        self.ocr_engine.set("RapidOCR")
        self.ocr_language.set("en")
        self.force_full_page_ocr.set(False)
        self.ocr_confidence.set(0.5)

        self.table_mode.set("Accurate")
        self.do_cell_matching.set(True)

        self.max_pages.set(0)
        self.max_file_size_mb.set(0)
        self.document_timeout.set(0)
        self.generate_page_images.set(False)
        self.generate_table_images.set(False)
        self.images_scale.set(1.0)

        self.device.set("auto")
        self.num_threads.set(4)
        self.use_flash_attention.set(False)

        self.output_directory.set(str(Path.home() / "Documents"))
        self.create_subfolder.set(False)
        self.overwrite_files.set(False)

        # Hide VLM frame if shown
        self.vlm_frame.pack_forget()

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
            # Register the listbox as a drop target
            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind('<<Drop>>', self.on_drop)

            # Add visual feedback on drag over
            self.file_listbox.dnd_bind('<<DragEnter>>', self.on_drag_enter)
            self.file_listbox.dnd_bind('<<DragLeave>>', self.on_drag_leave)

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
                    # Convert the document
                    result = self.converter.convert(filepath)

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


def main():
    """Main entry point"""
    # Use TkinterDnD if available for drag-drop support
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    DoclingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
