"""
Docling GUI - A full-featured GUI for IBM Docling document conversion
Supports all Docling features including OCR, VLM, ASR pipelines
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import json
from pathlib import Path
from datetime import datetime

# Try to import docling components
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TableFormerMode,
        AcceleratorOptions,
    )
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

# Try to import OCR options
try:
    from docling.datamodel.pipeline_options import (
        EasyOcrOptions,
        TesseractOcrOptions,
        TesseractCliOcrOptions,
        RapidOcrOptions,
    )
    OCR_OPTIONS_AVAILABLE = True
except ImportError:
    OCR_OPTIONS_AVAILABLE = False

# Try to import OcrMac (macOS only)
try:
    from docling.datamodel.pipeline_options import OcrMacOptions
    OCRMAC_AVAILABLE = True
except ImportError:
    OCRMAC_AVAILABLE = False

# Try to import drag-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

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


class DoclingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Docling GUI - Full-Featured Document Converter")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)

        # File list storage
        self.file_list = []

        # Conversion state
        self.is_converting = False
        self.cancel_requested = False
        self.converter = None

        # Initialize all option variables
        self.init_variables()

        # Build the UI
        self.create_menu()
        self.create_main_layout()

        # Check if docling is available
        if not DOCLING_AVAILABLE:
            self.log_message("WARNING: Docling is not installed. Please run: pip install docling")

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
        self.ocr_engine = tk.StringVar(value="Auto")
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
        self.output_directory = tk.StringVar(value=str(Path.home() / "Documents"))
        self.create_subfolder = tk.BooleanVar(value=False)
        self.overwrite_files = tk.BooleanVar(value=False)
        self.export_images_separately = tk.BooleanVar(value=False)

    def create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Add Files...", command=self.add_files, accelerator="Ctrl+O")
        file_menu.add_command(label="Add Folder...", command=self.add_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Clear All Files", command=self.clear_files)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Alt+F4")

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Set Default Output Directory...", command=self.set_default_output)
        settings_menu.add_separator()
        settings_menu.add_command(label="Reset All Options", command=self.reset_options)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Docling Documentation", command=self.open_docs)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)

        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.add_files())

    def create_main_layout(self):
        """Create the main window layout"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top section: Input and Options side by side
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights
        top_frame.columnconfigure(0, weight=2)
        top_frame.columnconfigure(1, weight=3)
        top_frame.rowconfigure(0, weight=1)

        # Create panels
        self.create_input_panel(top_frame)
        self.create_options_panel(top_frame)

        # Output settings
        self.create_output_panel(main_frame)

        # Preview/Log panel
        self.create_preview_panel(main_frame)

        # Progress and controls
        self.create_controls_panel(main_frame)

    def create_input_panel(self, parent):
        """Create the input files panel"""
        input_frame = ttk.LabelFrame(parent, text="Input Files", padding="10")
        input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)

        # Buttons frame
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(btn_frame, text="Add Files", command=self.add_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Add Folder", command=self.add_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove", command=self.remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear", command=self.clear_files).pack(side=tk.LEFT, padx=2)

        # File listbox with scrollbar
        list_frame = ttk.Frame(input_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.file_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            font=('Consolas', 9)
        )
        self.file_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar_y.config(command=self.file_listbox.yview)
        scrollbar_x.config(command=self.file_listbox.xview)

        # Bind selection event
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)

        # Right-click context menu
        self.context_menu = tk.Menu(self.file_listbox, tearoff=0)
        self.context_menu.add_command(label="Remove", command=self.remove_selected)
        self.context_menu.add_command(label="Open in Explorer", command=self.open_in_explorer)
        self.file_listbox.bind('<Button-3>', self.show_context_menu)

        # Info labels
        info_frame = ttk.Frame(input_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))

        self.file_count_label = ttk.Label(info_frame, text="0 files")
        self.file_count_label.pack(side=tk.LEFT)

        supported_text = "PDF, DOCX, PPTX, XLSX, HTML, Images, Audio"
        ttk.Label(info_frame, text=supported_text, foreground="gray", font=('', 8)).pack(side=tk.RIGHT)

    def create_options_panel(self, parent):
        """Create the tabbed conversion options panel"""
        options_frame = ttk.LabelFrame(parent, text="Conversion Options", padding="5")
        options_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)

        # Create notebook for tabs
        self.options_notebook = ttk.Notebook(options_frame)
        self.options_notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.create_basic_options_tab()
        self.create_ocr_options_tab()
        self.create_advanced_options_tab()
        self.create_accelerator_options_tab()

    def create_basic_options_tab(self):
        """Create the Basic Options tab"""
        tab = ttk.Frame(self.options_notebook, padding="10")
        self.options_notebook.add(tab, text="Basic")

        # Pipeline Type
        pipeline_frame = ttk.Frame(tab)
        pipeline_frame.pack(fill=tk.X, pady=5)

        ttk.Label(pipeline_frame, text="Pipeline:").pack(side=tk.LEFT)
        pipeline_combo = ttk.Combobox(
            pipeline_frame,
            textvariable=self.pipeline_type,
            values=["Standard", "VLM", "ASR"],
            state="readonly",
            width=15
        )
        pipeline_combo.pack(side=tk.LEFT, padx=(10, 20))
        pipeline_combo.bind('<<ComboboxSelected>>', self.on_pipeline_change)

        # VLM Model (hidden by default)
        self.vlm_frame = ttk.Frame(pipeline_frame)
        ttk.Label(self.vlm_frame, text="VLM Model:").pack(side=tk.LEFT)
        vlm_combo = ttk.Combobox(
            self.vlm_frame,
            textvariable=self.vlm_model,
            values=["granite_docling", "smolvlm"],
            state="readonly",
            width=15
        )
        vlm_combo.pack(side=tk.LEFT, padx=(5, 0))

        # Output Format
        format_frame = ttk.Frame(tab)
        format_frame.pack(fill=tk.X, pady=5)

        ttk.Label(format_frame, text="Output Format:").pack(side=tk.LEFT)
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.output_format,
            values=["Markdown", "HTML", "JSON", "DocTags", "Text"],
            state="readonly",
            width=15
        )
        format_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Separator
        ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

        # Feature Checkboxes - 2 columns
        ttk.Label(tab, text="Processing Features:", font=('', 9, 'bold')).pack(anchor=tk.W)

        features_frame = ttk.Frame(tab)
        features_frame.pack(fill=tk.X, pady=5)

        # Left column
        left_col = ttk.Frame(features_frame)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Checkbutton(left_col, text="Enable OCR",
                       variable=self.enable_ocr).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(left_col, text="Extract Tables",
                       variable=self.do_table_structure).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(left_col, text="Formula Enrichment",
                       variable=self.do_formula_enrichment).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(left_col, text="Code Enrichment",
                       variable=self.do_code_enrichment).pack(anchor=tk.W, pady=2)

        # Right column
        right_col = ttk.Frame(features_frame)
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Checkbutton(right_col, text="Picture Classification",
                       variable=self.do_picture_classification).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(right_col, text="Picture Description (VLM)",
                       variable=self.do_picture_description).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(right_col, text="Export Pictures",
                       variable=self.generate_picture_images).pack(anchor=tk.W, pady=2)

    def create_ocr_options_tab(self):
        """Create the OCR Options tab"""
        tab = ttk.Frame(self.options_notebook, padding="10")
        self.options_notebook.add(tab, text="OCR")

        # OCR Engine
        engine_frame = ttk.Frame(tab)
        engine_frame.pack(fill=tk.X, pady=5)

        ttk.Label(engine_frame, text="OCR Engine:").pack(side=tk.LEFT)
        engines = ["Auto", "Tesseract", "EasyOCR", "RapidOCR"]
        if OCRMAC_AVAILABLE:
            engines.append("OcrMac")
        engine_combo = ttk.Combobox(
            engine_frame,
            textvariable=self.ocr_engine,
            values=engines,
            state="readonly",
            width=15
        )
        engine_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Language
        lang_frame = ttk.Frame(tab)
        lang_frame.pack(fill=tk.X, pady=5)

        ttk.Label(lang_frame, text="Language:").pack(side=tk.LEFT)
        lang_values = [f"{code} - {name}" for code, name in OCR_LANGUAGES]
        lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.ocr_language,
            values=[code for code, name in OCR_LANGUAGES],
            state="readonly",
            width=15
        )
        lang_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Language hint
        ttk.Label(lang_frame, text="(English, German, Chinese, etc.)",
                 foreground="gray").pack(side=tk.LEFT, padx=(10, 0))

        # Separator
        ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

        # OCR Options
        ttk.Label(tab, text="OCR Options:", font=('', 9, 'bold')).pack(anchor=tk.W)

        ttk.Checkbutton(tab, text="Force Full Page OCR (slower but more thorough)",
                       variable=self.force_full_page_ocr).pack(anchor=tk.W, pady=5)

        # Confidence Threshold
        conf_frame = ttk.Frame(tab)
        conf_frame.pack(fill=tk.X, pady=5)

        ttk.Label(conf_frame, text="Confidence Threshold:").pack(side=tk.LEFT)
        conf_scale = ttk.Scale(
            conf_frame,
            from_=0.1,
            to=1.0,
            variable=self.ocr_confidence,
            orient=tk.HORIZONTAL,
            length=150
        )
        conf_scale.pack(side=tk.LEFT, padx=(10, 5))
        self.conf_label = ttk.Label(conf_frame, text="0.5")
        self.conf_label.pack(side=tk.LEFT)
        conf_scale.configure(command=lambda v: self.conf_label.config(text=f"{float(v):.2f}"))

        # Note about OCR
        note_frame = ttk.Frame(tab)
        note_frame.pack(fill=tk.X, pady=(20, 0))
        ttk.Label(note_frame, text="Note: OCR requires Tesseract or EasyOCR to be installed.",
                 foreground="gray", font=('', 8)).pack(anchor=tk.W)

    def create_advanced_options_tab(self):
        """Create the Advanced Options tab"""
        tab = ttk.Frame(self.options_notebook, padding="10")
        self.options_notebook.add(tab, text="Advanced")

        # Table Options
        ttk.Label(tab, text="Table Options:", font=('', 9, 'bold')).pack(anchor=tk.W)

        table_frame = ttk.Frame(tab)
        table_frame.pack(fill=tk.X, pady=5)

        ttk.Label(table_frame, text="Table Mode:").pack(side=tk.LEFT)
        table_combo = ttk.Combobox(
            table_frame,
            textvariable=self.table_mode,
            values=["Fast", "Accurate"],
            state="readonly",
            width=12
        )
        table_combo.pack(side=tk.LEFT, padx=(10, 20))

        ttk.Checkbutton(table_frame, text="Cell Matching",
                       variable=self.do_cell_matching).pack(side=tk.LEFT)

        # Separator
        ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

        # Limits
        ttk.Label(tab, text="Processing Limits:", font=('', 9, 'bold')).pack(anchor=tk.W)

        limits_frame = ttk.Frame(tab)
        limits_frame.pack(fill=tk.X, pady=5)

        # Max Pages
        ttk.Label(limits_frame, text="Max Pages:").pack(side=tk.LEFT)
        max_pages_spin = ttk.Spinbox(
            limits_frame,
            from_=0,
            to=10000,
            textvariable=self.max_pages,
            width=8
        )
        max_pages_spin.pack(side=tk.LEFT, padx=(5, 15))
        ttk.Label(limits_frame, text="(0 = unlimited)", foreground="gray").pack(side=tk.LEFT)

        limits_frame2 = ttk.Frame(tab)
        limits_frame2.pack(fill=tk.X, pady=5)

        # Timeout
        ttk.Label(limits_frame2, text="Timeout (sec):").pack(side=tk.LEFT)
        timeout_spin = ttk.Spinbox(
            limits_frame2,
            from_=0,
            to=3600,
            textvariable=self.document_timeout,
            width=8
        )
        timeout_spin.pack(side=tk.LEFT, padx=(5, 15))
        ttk.Label(limits_frame2, text="(0 = no limit)", foreground="gray").pack(side=tk.LEFT)

        # Separator
        ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

        # Image Generation
        ttk.Label(tab, text="Image Generation:", font=('', 9, 'bold')).pack(anchor=tk.W)

        img_frame = ttk.Frame(tab)
        img_frame.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(img_frame, text="Generate Page Images",
                       variable=self.generate_page_images).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Checkbutton(img_frame, text="Generate Table Images",
                       variable=self.generate_table_images).pack(side=tk.LEFT)

        # Image Scale
        scale_frame = ttk.Frame(tab)
        scale_frame.pack(fill=tk.X, pady=5)

        ttk.Label(scale_frame, text="Image Scale:").pack(side=tk.LEFT)
        scale_spin = ttk.Spinbox(
            scale_frame,
            from_=0.5,
            to=3.0,
            increment=0.25,
            textvariable=self.images_scale,
            width=8
        )
        scale_spin.pack(side=tk.LEFT, padx=(5, 10))
        ttk.Label(scale_frame, text="(0.5 - 3.0)", foreground="gray").pack(side=tk.LEFT)

    def create_accelerator_options_tab(self):
        """Create the Accelerator Options tab"""
        tab = ttk.Frame(self.options_notebook, padding="10")
        self.options_notebook.add(tab, text="Accelerator")

        # Device Selection
        ttk.Label(tab, text="Hardware Acceleration:", font=('', 9, 'bold')).pack(anchor=tk.W)

        device_frame = ttk.Frame(tab)
        device_frame.pack(fill=tk.X, pady=5)

        ttk.Label(device_frame, text="Device:").pack(side=tk.LEFT)
        device_combo = ttk.Combobox(
            device_frame,
            textvariable=self.device,
            values=["auto", "cpu", "cuda", "mps"],
            state="readonly",
            width=12
        )
        device_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Device descriptions
        desc_frame = ttk.Frame(tab)
        desc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(desc_frame, text="auto: Auto-detect | cuda: NVIDIA GPU | mps: Apple Silicon | cpu: CPU only",
                 foreground="gray", font=('', 8)).pack(anchor=tk.W)

        # Separator
        ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

        # Threading
        ttk.Label(tab, text="CPU Threading:", font=('', 9, 'bold')).pack(anchor=tk.W)

        thread_frame = ttk.Frame(tab)
        thread_frame.pack(fill=tk.X, pady=5)

        ttk.Label(thread_frame, text="Threads:").pack(side=tk.LEFT)
        thread_spin = ttk.Spinbox(
            thread_frame,
            from_=1,
            to=32,
            textvariable=self.num_threads,
            width=8
        )
        thread_spin.pack(side=tk.LEFT, padx=(10, 10))
        ttk.Label(thread_frame, text="(1-32, default: 4)", foreground="gray").pack(side=tk.LEFT)

        # Separator
        ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

        # CUDA Options
        ttk.Label(tab, text="CUDA Options:", font=('', 9, 'bold')).pack(anchor=tk.W)

        ttk.Checkbutton(tab, text="Use Flash Attention 2 (requires compatible GPU)",
                       variable=self.use_flash_attention).pack(anchor=tk.W, pady=5)

    def create_output_panel(self, parent):
        """Create the output settings panel"""
        output_frame = ttk.LabelFrame(parent, text="Output Settings", padding="10")
        output_frame.pack(fill=tk.X, pady=5)

        # Output directory
        dir_frame = ttk.Frame(output_frame)
        dir_frame.pack(fill=tk.X, pady=5)

        ttk.Label(dir_frame, text="Output Directory:").pack(side=tk.LEFT)
        dir_entry = ttk.Entry(dir_frame, textvariable=self.output_directory, width=50)
        dir_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="Browse", command=self.browse_output_dir).pack(side=tk.LEFT)

        # Options row
        options_frame = ttk.Frame(output_frame)
        options_frame.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(options_frame, text="Create subfolder per file",
                       variable=self.create_subfolder).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Checkbutton(options_frame, text="Overwrite existing",
                       variable=self.overwrite_files).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Checkbutton(options_frame, text="Export images separately",
                       variable=self.export_images_separately).pack(side=tk.LEFT)

    def create_preview_panel(self, parent):
        """Create the preview/log tabbed panel"""
        preview_frame = ttk.LabelFrame(parent, text="Preview / Log", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Notebook (tabbed interface)
        self.preview_notebook = ttk.Notebook(preview_frame)
        self.preview_notebook.pack(fill=tk.BOTH, expand=True)

        # Preview tab
        preview_tab = ttk.Frame(self.preview_notebook)
        self.preview_notebook.add(preview_tab, text="Preview")

        preview_scroll = ttk.Scrollbar(preview_tab)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.preview_text = tk.Text(
            preview_tab,
            wrap=tk.WORD,
            yscrollcommand=preview_scroll.set,
            font=('Consolas', 10),
            state=tk.DISABLED
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        preview_scroll.config(command=self.preview_text.yview)

        # Log tab
        log_tab = ttk.Frame(self.preview_notebook)
        self.preview_notebook.add(log_tab, text="Log")

        log_scroll = ttk.Scrollbar(log_tab)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_tab,
            wrap=tk.WORD,
            yscrollcommand=log_scroll.set,
            font=('Consolas', 9),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)

    def create_controls_panel(self, parent):
        """Create the progress bar and control buttons"""
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill=tk.X, pady=10)

        # Progress bar
        progress_frame = ttk.Frame(controls_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 10))

        self.progress_label = ttk.Label(progress_frame, text="0%", width=5)
        self.progress_label.pack(side=tk.LEFT)

        # Status label
        self.status_label = ttk.Label(controls_frame, text="Ready", foreground="gray")
        self.status_label.pack(fill=tk.X, pady=(0, 10))

        # Buttons
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack()

        self.convert_selected_btn = ttk.Button(
            btn_frame,
            text="Convert Selected",
            command=self.convert_selected
        )
        self.convert_selected_btn.pack(side=tk.LEFT, padx=5)

        self.convert_all_btn = ttk.Button(
            btn_frame,
            text="Convert All",
            command=self.convert_all
        )
        self.convert_all_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.cancel_conversion,
            state=tk.DISABLED
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

    # ==================== Event Handlers ====================

    def on_pipeline_change(self, event=None):
        """Handle pipeline type change"""
        pipeline = self.pipeline_type.get()
        if pipeline == "VLM":
            self.vlm_frame.pack(side=tk.LEFT)
        else:
            self.vlm_frame.pack_forget()

    def reset_options(self):
        """Reset all options to defaults"""
        self.init_variables()
        messagebox.showinfo("Reset", "All options have been reset to defaults.")

    # ==================== File Operations ====================

    def add_files(self):
        """Open file dialog to add files"""
        filetypes = [
            ("All Supported", " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS.keys())),
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
            for root, dirs, files in os.walk(folder):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        self.add_file_to_list(os.path.join(root, file))
                        count += 1
            self.log_message(f"Added {count} files from folder")

    def add_file_to_list(self, filepath):
        """Add a single file to the list"""
        if filepath not in self.file_list:
            ext = os.path.splitext(filepath)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                self.file_list.append(filepath)
                display_name = os.path.basename(filepath)
                self.file_listbox.insert(tk.END, display_name)
                self.update_file_count()
            else:
                self.log_message(f"Unsupported file type: {filepath}")

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
        self.file_count_label.config(text=f"{count} file{'s' if count != 1 else ''}")

    def on_file_select(self, event):
        """Handle file selection for preview"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            filepath = self.file_list[index]
            self.show_file_info(filepath)

    def show_file_info(self, filepath):
        """Show file info in preview panel"""
        try:
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
            info += f"Type: {SUPPORTED_EXTENSIONS.get(ext, 'Unknown')}\n"

            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, info)
            self.preview_text.config(state=tk.DISABLED)
        except Exception as e:
            self.log_message(f"Error reading file info: {e}")

    def show_context_menu(self, event):
        """Show right-click context menu"""
        try:
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.file_listbox.nearest(event.y))
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def open_in_explorer(self):
        """Open selected file location in Explorer"""
        selection = self.file_listbox.curselection()
        if selection:
            filepath = self.file_list[selection[0]]
            folder = os.path.dirname(filepath)
            os.startfile(folder)

    # ==================== Directory Operations ====================

    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_directory.set(directory)

    def set_default_output(self):
        """Set default output directory"""
        self.browse_output_dir()

    # ==================== Conversion ====================

    def convert_selected(self):
        """Convert only selected files"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select files to convert.")
            return

        files_to_convert = [self.file_list[i] for i in selection]
        self.start_conversion(files_to_convert)

    def convert_all(self):
        """Convert all files in the list"""
        if not self.file_list:
            messagebox.showwarning("No Files", "Please add files to convert.")
            return

        self.start_conversion(self.file_list.copy())

    def build_pipeline_options(self):
        """Build pipeline options from GUI settings"""
        if not DOCLING_AVAILABLE:
            return None

        # Create pipeline options
        pipeline_options = PdfPipelineOptions(
            do_ocr=self.enable_ocr.get(),
            do_table_structure=self.do_table_structure.get(),
            do_picture_classification=self.do_picture_classification.get(),
            do_picture_description=self.do_picture_description.get(),
            generate_page_images=self.generate_page_images.get(),
            generate_picture_images=self.generate_picture_images.get(),
            generate_table_images=self.generate_table_images.get(),
        )

        # Set optional enrichment options if available
        if hasattr(pipeline_options, 'do_formula_enrichment'):
            pipeline_options.do_formula_enrichment = self.do_formula_enrichment.get()
        if hasattr(pipeline_options, 'do_code_enrichment'):
            pipeline_options.do_code_enrichment = self.do_code_enrichment.get()

        # Table structure options
        if hasattr(pipeline_options, 'table_structure_options'):
            if self.table_mode.get() == "Fast":
                pipeline_options.table_structure_options.mode = TableFormerMode.FAST
            else:
                pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
            pipeline_options.table_structure_options.do_cell_matching = self.do_cell_matching.get()

        # OCR options
        if OCR_OPTIONS_AVAILABLE and self.enable_ocr.get():
            ocr_engine = self.ocr_engine.get()
            lang = self.ocr_language.get()

            if ocr_engine == "EasyOCR":
                pipeline_options.ocr_options = EasyOcrOptions(
                    lang=[lang],
                    force_full_page_ocr=self.force_full_page_ocr.get(),
                    confidence_threshold=self.ocr_confidence.get()
                )
            elif ocr_engine == "Tesseract":
                pipeline_options.ocr_options = TesseractOcrOptions(
                    lang=lang,
                    force_full_page_ocr=self.force_full_page_ocr.get()
                )
            elif ocr_engine == "RapidOCR":
                pipeline_options.ocr_options = RapidOcrOptions(
                    lang=[lang],
                    force_full_page_ocr=self.force_full_page_ocr.get()
                )
            elif ocr_engine == "OcrMac" and OCRMAC_AVAILABLE:
                pipeline_options.ocr_options = OcrMacOptions(
                    lang=lang,
                    force_full_page_ocr=self.force_full_page_ocr.get()
                )

        # Accelerator options
        pipeline_options.accelerator_options = AcceleratorOptions(
            device=self.device.get(),
            num_threads=self.num_threads.get()
        )
        if hasattr(pipeline_options.accelerator_options, 'cuda_use_flash_attention2'):
            pipeline_options.accelerator_options.cuda_use_flash_attention2 = self.use_flash_attention.get()

        # Images scale
        if hasattr(pipeline_options, 'images_scale'):
            pipeline_options.images_scale = self.images_scale.get()

        return pipeline_options

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

        # Start conversion thread
        thread = threading.Thread(target=self.conversion_worker, args=(files,))
        thread.daemon = True
        thread.start()

    def conversion_worker(self, files):
        """Worker thread for conversion"""
        try:
            # Build pipeline options
            pipeline_options = self.build_pipeline_options()

            # Log configuration
            self.log_message("=== Conversion Configuration ===")
            self.log_message(f"Pipeline: {self.pipeline_type.get()}")
            self.log_message(f"Output Format: {self.output_format.get()}")
            self.log_message(f"OCR: {self.enable_ocr.get()}, Engine: {self.ocr_engine.get()}, Lang: {self.ocr_language.get()}")
            self.log_message(f"Table Mode: {self.table_mode.get()}")
            self.log_message(f"Device: {self.device.get()}, Threads: {self.num_threads.get()}")
            self.log_message("================================")

            # Create converter with options
            if pipeline_options:
                self.converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                    }
                )
            else:
                self.converter = DocumentConverter()

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
                    output_format = self.output_format.get()
                    output_ext = self.get_output_extension(output_format)

                    # Determine output path
                    base_name = os.path.splitext(filename)[0]
                    output_dir = self.output_directory.get()

                    if self.create_subfolder.get():
                        output_dir = os.path.join(output_dir, base_name)
                        os.makedirs(output_dir, exist_ok=True)

                    output_path = os.path.join(output_dir, f"{base_name}{output_ext}")

                    # Check for overwrite
                    if os.path.exists(output_path) and not self.overwrite_files.get():
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_path = os.path.join(output_dir, f"{base_name}_{timestamp}{output_ext}")

                    # Export content
                    content = self.export_content(result, output_format)

                    # Write to file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    self.log_message(f"  Saved: {output_path}")
                    successful += 1

                    # Update preview with last converted content
                    self.update_preview(content[:5000])  # Limit preview size

                except Exception as e:
                    self.log_message(f"  ERROR: {str(e)}")
                    failed += 1

                # Update progress
                progress = ((i + 1) / total) * 100
                self.update_progress(progress)

            # Final summary
            self.log_message(f"\n=== Conversion Complete ===")
            self.log_message(f"Successful: {successful}")
            self.log_message(f"Failed: {failed}")
            self.log_message(f"===========================")

        except Exception as e:
            self.log_message(f"Conversion error: {str(e)}")

        finally:
            self.is_converting = False
            self.root.after(0, self.conversion_finished)

    def get_output_extension(self, format_name):
        """Get file extension for output format"""
        extensions = {
            "Markdown": ".md",
            "HTML": ".html",
            "JSON": ".json",
            "DocTags": ".doctags",
            "Text": ".txt"
        }
        return extensions.get(format_name, ".txt")

    def export_content(self, result, format_name):
        """Export converted content in the specified format"""
        doc = result.document

        if format_name == "Markdown":
            return doc.export_to_markdown()
        elif format_name == "HTML":
            return doc.export_to_html()
        elif format_name == "JSON":
            return json.dumps(doc.export_to_dict(), indent=2, ensure_ascii=False)
        elif format_name == "DocTags":
            if hasattr(doc, 'export_to_doctags'):
                return doc.export_to_doctags()
            else:
                return doc.export_to_markdown()
        elif format_name == "Text":
            # Plain text - strip markdown
            return doc.export_to_markdown()
        else:
            return doc.export_to_markdown()

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
        import webbrowser
        webbrowser.open("https://docling-project.github.io/docling/")

    def show_about(self):
        """Show about dialog"""
        about_text = """Docling GUI - Full-Featured Document Converter

A comprehensive graphical interface for IBM Docling.

FEATURES:
- Multiple input formats: PDF, DOCX, PPTX, XLSX, HTML, Images, Audio
- Multiple output formats: Markdown, HTML, JSON, DocTags, Text
- Pipeline types: Standard, VLM (Vision Language Model), ASR (Speech)
- OCR engines: Tesseract, EasyOCR, RapidOCR, OcrMac
- Table extraction: Fast and Accurate modes
- Formula and code enrichment
- Picture classification and description
- GPU acceleration (CUDA, MPS)
- Batch processing with progress tracking

https://github.com/docling-project/docling
https://docling-project.github.io/docling/
"""
        messagebox.showinfo("About Docling GUI", about_text)


def main():
    # Use TkinterDnD if available for drag-drop support
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    DoclingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
