"""
GUI Panels and Layout Components for Docling GUI.
This module separates the UI construction code from the main controller logic.
"""
import tkinter as tk
from tkinter import ttk
import config
from tooltip import create_tooltip


def create_menu(gui):
    """Create the menu bar"""
    menubar = tk.Menu(gui.root)
    gui.root.config(menu=menubar)

    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Add Files...",
                          command=gui.add_files, accelerator="Ctrl+O")
    file_menu.add_command(label="Add Folder...", command=gui.add_folder)
    file_menu.add_separator()
    file_menu.add_command(label="Clear All Files",
                          command=gui.clear_files)
    file_menu.add_separator()
    file_menu.add_command(
        label="Exit", command=gui.root.quit, accelerator="Alt+F4")

    # Settings menu
    settings_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Settings", menu=settings_menu)
    settings_menu.add_command(
        label="Set Default Output Directory...", command=gui.set_default_output
    )
    settings_menu.add_separator()
    settings_menu.add_command(
        label="Reset All Options", command=gui.reset_options)

    # Help menu
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(
        label="Docling Documentation", command=gui.open_docs)
    help_menu.add_separator()
    help_menu.add_command(label="About", command=gui.show_about)

    # Keyboard shortcuts
    gui.root.bind('<Control-o>', lambda e: gui.add_files())


def create_input_panel(gui, parent):
    """Create the input files panel"""
    input_frame = ttk.LabelFrame(parent, text="Input Files", padding="10")
    input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)

    # Buttons frame
    btn_frame = ttk.Frame(input_frame)
    btn_frame.pack(fill=tk.X, pady=(0, 10))

    ttk.Button(btn_frame, text="Add Files",
               command=gui.add_files).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Add Folder",
               command=gui.add_folder).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Remove", command=gui.remove_selected).pack(
        side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="Clear", command=gui.clear_files).pack(
        side=tk.LEFT, padx=2)

    # File listbox with scrollbar
    list_frame = ttk.Frame(input_frame)
    list_frame.pack(fill=tk.BOTH, expand=True)

    scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
    scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

    scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
    scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

    gui.file_listbox = tk.Listbox(
        list_frame,
        selectmode=tk.EXTENDED,
        yscrollcommand=scrollbar_y.set,
        xscrollcommand=scrollbar_x.set,
        font=('Consolas', 9)
    )
    gui.file_listbox.pack(fill=tk.BOTH, expand=True)
    scrollbar_y.config(command=gui.file_listbox.yview)
    scrollbar_x.config(command=gui.file_listbox.xview)

    # Bind selection event
    gui.file_listbox.bind('<<ListboxSelect>>', gui.on_file_select)

    # Right-click context menu
    gui.context_menu = tk.Menu(gui.file_listbox, tearoff=0)
    gui.context_menu.add_command(
        label="Remove", command=gui.remove_selected)
    gui.context_menu.add_command(
        label="Open in Explorer", command=gui.open_in_explorer)
    gui.file_listbox.bind('<Button-3>', gui.show_context_menu)

    # Info labels
    info_frame = ttk.Frame(input_frame)
    info_frame.pack(fill=tk.X, pady=(5, 0))

    gui.file_count_label = ttk.Label(info_frame, text="0 files")
    gui.file_count_label.pack(side=tk.LEFT)

    # Drag and drop hint
    ttk.Label(
        info_frame, text="💡 Drag & drop files/folders here",
        foreground="#2563eb", font=('', 8, 'italic')
    ).pack(side=tk.LEFT, padx=(10, 0))

    supported_text = "PDF, DOCX, PPTX, XLSX, HTML, Images, Audio"
    ttk.Label(
        info_frame, text=supported_text, foreground="gray", font=('', 8)
    ).pack(side=tk.RIGHT)


def create_options_panel(gui, parent):
    """Create the tabbed conversion options panel"""
    options_frame = ttk.LabelFrame(
        parent, text="Conversion Options", padding="5")
    options_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)

    # Create notebook for tabs
    gui.options_notebook = ttk.Notebook(options_frame)
    gui.options_notebook.pack(fill=tk.BOTH, expand=True)

    # Create tabs
    _create_basic_options_tab(gui)
    _create_ocr_options_tab(gui)
    _create_advanced_options_tab(gui)
    _create_accelerator_options_tab(gui)


def _create_basic_options_tab(gui):
    """Create the Basic Options tab (Internal helper)"""
    tab = ttk.Frame(gui.options_notebook, padding="10")
    gui.options_notebook.add(tab, text="Basic")

    # Pipeline Type
    pipeline_frame = ttk.Frame(tab)
    pipeline_frame.pack(fill=tk.X, pady=5)

    ttk.Label(pipeline_frame, text="Pipeline:").pack(side=tk.LEFT)
    pipeline_combo = ttk.Combobox(
        pipeline_frame,
        textvariable=gui.pipeline_type,
        values=["Standard", "VLM", "ASR"],
        state="readonly",
        width=15
    )
    pipeline_combo.pack(side=tk.LEFT, padx=(10, 20))
    pipeline_combo.bind('<<ComboboxSelected>>', gui.on_pipeline_change)
    create_tooltip(
        pipeline_combo,
        "Standard: Default processing\n"
        "VLM: Vision Language Model for advanced image understanding\n"
        "ASR: Automatic Speech Recognition for audio files"
    )

    # VLM Model (hidden by default)
    gui.vlm_frame = ttk.Frame(pipeline_frame)
    ttk.Label(gui.vlm_frame, text="VLM Model:").pack(side=tk.LEFT)
    vlm_combo = ttk.Combobox(
        gui.vlm_frame,
        textvariable=gui.vlm_model,
        values=["granite_docling", "smolvlm"],
        state="readonly",
        width=15
    )
    vlm_combo.pack(side=tk.LEFT, padx=(5, 0))
    create_tooltip(
        vlm_combo,
        "Vision Language Model for image description:\n"
        "granite_docling: IBM's specialized model\n"
        "smolvlm: Smaller, faster alternative"
    )

    # Output Format
    format_frame = ttk.Frame(tab)
    format_frame.pack(fill=tk.X, pady=5)

    ttk.Label(format_frame, text="Output Format:").pack(side=tk.LEFT)
    format_combo = ttk.Combobox(
        format_frame,
        textvariable=gui.output_format,
        values=["Markdown", "HTML", "JSON", "DocTags", "Text"],
        state="readonly",
        width=15
    )
    format_combo.pack(side=tk.LEFT, padx=(10, 0))
    create_tooltip(
        format_combo,
        "Choose output format:\n"
        "Markdown: Easy to read, widely compatible\n"
        "HTML: For web display\n"
        "JSON: Structured data with metadata\n"
        "Text: Plain text only"
    )

    # Separator
    ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

    # Feature Checkboxes - 2 columns
    ttk.Label(tab, text="Processing Features:",
              font=('', 9, 'bold')).pack(anchor=tk.W)

    features_frame = ttk.Frame(tab)
    features_frame.pack(fill=tk.X, pady=5)

    # Left column
    left_col = ttk.Frame(features_frame)
    left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    ocr_check = ttk.Checkbutton(left_col, text="Enable OCR",
                                variable=gui.enable_ocr)
    ocr_check.pack(anchor=tk.W, pady=2)
    create_tooltip(ocr_check, "Extract text from images and scanned documents")

    table_check = ttk.Checkbutton(left_col, text="Extract Tables",
                                  variable=gui.do_table_structure)
    table_check.pack(anchor=tk.W, pady=2)
    create_tooltip(
        table_check, "Detect and extract table structures with cell data")

    formula_check = ttk.Checkbutton(left_col, text="Formula Enrichment",
                                    variable=gui.do_formula_enrichment)
    formula_check.pack(anchor=tk.W, pady=2)
    create_tooltip(
        formula_check, "Detect and convert mathematical formulas to LaTeX")

    code_check = ttk.Checkbutton(left_col, text="Code Enrichment",
                                 variable=gui.do_code_enrichment)
    code_check.pack(anchor=tk.W, pady=2)
    create_tooltip(code_check, "Detect and preserve code blocks with syntax")

    # Right column
    right_col = ttk.Frame(features_frame)
    right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    pic_class_check = ttk.Checkbutton(right_col, text="Picture Classification",
                                      variable=gui.do_picture_classification)
    pic_class_check.pack(anchor=tk.W, pady=2)
    create_tooltip(pic_class_check,
                   "Classify images (chart, diagram, photo, etc.)")

    pic_desc_check = ttk.Checkbutton(right_col, text="Picture Description (VLM)",
                                     variable=gui.do_picture_description)
    pic_desc_check.pack(anchor=tk.W, pady=2)
    create_tooltip(
        pic_desc_check, "Generate AI descriptions for images (requires VLM)")

    export_pic_check = ttk.Checkbutton(right_col, text="Export Pictures",
                                       variable=gui.generate_picture_images)
    export_pic_check.pack(anchor=tk.W, pady=2)
    create_tooltip(export_pic_check, "Save extracted images as separate files")


def _create_ocr_options_tab(gui):
    """Create the OCR Options tab (Internal helper)"""
    tab = ttk.Frame(gui.options_notebook, padding="10")
    gui.options_notebook.add(tab, text="OCR")

    # OCR Engine
    engine_frame = ttk.Frame(tab)
    engine_frame.pack(fill=tk.X, pady=5)

    ttk.Label(engine_frame, text="OCR Engine:").pack(side=tk.LEFT)
    engines = ["Auto", "RapidOCR", "EasyOCR"]
    engine_combo = ttk.Combobox(
        engine_frame,
        textvariable=gui.ocr_engine,
        values=engines,
        state="readonly",
        width=15
    )
    engine_combo.pack(side=tk.LEFT, padx=(10, 0))
    create_tooltip(
        engine_combo,
        "OCR Engine Selection:\n"
        "Auto: Uses RapidOCR (recommended)\n"
        "RapidOCR: Fast, built-in engine\n"
        "EasyOCR: Deep learning-based (requires installation)"
    )

    # Language
    lang_frame = ttk.Frame(tab)
    lang_frame.pack(fill=tk.X, pady=5)

    ttk.Label(lang_frame, text="Language:").pack(side=tk.LEFT)

    lang_combo = ttk.Combobox(
        lang_frame,
        textvariable=gui.ocr_language,
        values=[code for code, name in config.OCR_LANGUAGES],
        state="readonly",
        width=15
    )
    lang_combo.pack(side=tk.LEFT, padx=(10, 0))
    create_tooltip(
        lang_combo, "Select the primary language for OCR text recognition")

    # Language hint
    ttk.Label(lang_frame, text="(English, German, Chinese, etc.)",
              foreground="gray").pack(side=tk.LEFT, padx=(10, 0))

    # Separator
    ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

    # OCR Options
    ttk.Label(tab, text="OCR Options:", font=(
        '', 9, 'bold')).pack(anchor=tk.W)

    ttk.Checkbutton(tab, text="Force Full Page OCR (slower but more thorough)",
                    variable=gui.force_full_page_ocr).pack(anchor=tk.W, pady=5)

    # Confidence Threshold
    conf_frame = ttk.Frame(tab)
    conf_frame.pack(fill=tk.X, pady=5)

    ttk.Label(conf_frame, text="Confidence Threshold:").pack(side=tk.LEFT)
    conf_scale = ttk.Scale(
        conf_frame,
        from_=0.1,
        to=1.0,
        variable=gui.ocr_confidence,
        orient=tk.HORIZONTAL,
        length=150
    )
    conf_scale.pack(side=tk.LEFT, padx=(10, 5))
    gui.conf_label = ttk.Label(conf_frame, text="0.5")
    gui.conf_label.pack(side=tk.LEFT)
    conf_scale.configure(
        command=lambda v: gui.conf_label.config(text=f"{float(v):.2f}"))

    # Note about OCR
    note_frame = ttk.Frame(tab)
    note_frame.pack(fill=tk.X, pady=(20, 0))
    ttk.Label(
        note_frame,
        text="Note: RapidOCR is built-in. EasyOCR requires separate installation.",
        foreground="gray", font=('', 8)
    ).pack(anchor=tk.W)


def _create_advanced_options_tab(gui):
    """Create the Advanced Options tab (Internal helper)"""
    tab = ttk.Frame(gui.options_notebook, padding="10")
    gui.options_notebook.add(tab, text="Advanced")

    # Table Options
    ttk.Label(tab, text="Table Options:", font=(
        '', 9, 'bold')).pack(anchor=tk.W)

    table_frame = ttk.Frame(tab)
    table_frame.pack(fill=tk.X, pady=5)

    ttk.Label(table_frame, text="Table Mode:").pack(side=tk.LEFT)
    table_combo = ttk.Combobox(
        table_frame,
        textvariable=gui.table_mode,
        values=["Fast", "Accurate"],
        state="readonly",
        width=12
    )
    table_combo.pack(side=tk.LEFT, padx=(10, 20))

    ttk.Checkbutton(table_frame, text="Cell Matching",
                    variable=gui.do_cell_matching).pack(side=tk.LEFT)

    # Separator
    ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

    # Limits
    ttk.Label(tab, text="Processing Limits:",
              font=('', 9, 'bold')).pack(anchor=tk.W)

    limits_frame = ttk.Frame(tab)
    limits_frame.pack(fill=tk.X, pady=5)

    # Max Pages
    ttk.Label(limits_frame, text="Max Pages:").pack(side=tk.LEFT)
    ttk.Spinbox(
        limits_frame,
        from_=0,
        to=10000,
        textvariable=gui.max_pages,
        width=8
    ).pack(side=tk.LEFT, padx=(5, 15))
    ttk.Label(limits_frame, text="(0 = unlimited)",
              foreground="gray").pack(side=tk.LEFT)

    limits_frame2 = ttk.Frame(tab)
    limits_frame2.pack(fill=tk.X, pady=5)

    # Timeout
    ttk.Label(limits_frame2, text="Timeout (sec):").pack(side=tk.LEFT)
    ttk.Spinbox(
        limits_frame2,
        from_=0,
        to=3600,
        textvariable=gui.document_timeout,
        width=8
    ).pack(side=tk.LEFT, padx=(5, 15))
    ttk.Label(limits_frame2, text="(0 = no limit)",
              foreground="gray").pack(side=tk.LEFT)

    # Separator
    ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

    # Image Generation
    ttk.Label(tab, text="Image Generation:",
              font=('', 9, 'bold')).pack(anchor=tk.W)

    img_frame = ttk.Frame(tab)
    img_frame.pack(fill=tk.X, pady=5)

    ttk.Checkbutton(img_frame, text="Generate Page Images",
                    variable=gui.generate_page_images).pack(side=tk.LEFT, padx=(0, 15))
    ttk.Checkbutton(img_frame, text="Generate Table Images",
                    variable=gui.generate_table_images).pack(side=tk.LEFT)

    # Image Scale
    scale_frame = ttk.Frame(tab)
    scale_frame.pack(fill=tk.X, pady=5)

    ttk.Label(scale_frame, text="Image Scale:").pack(side=tk.LEFT)
    ttk.Spinbox(
        scale_frame,
        from_=0.5,
        to=3.0,
        increment=0.25,
        textvariable=gui.images_scale,
        width=8
    ).pack(side=tk.LEFT, padx=(5, 10))
    ttk.Label(scale_frame, text="(0.5 - 3.0)",
              foreground="gray").pack(side=tk.LEFT)


def _create_accelerator_options_tab(gui):
    """Create the Accelerator Options tab (Internal helper)"""
    tab = ttk.Frame(gui.options_notebook, padding="10")
    gui.options_notebook.add(tab, text="Accelerator")

    # Device Selection
    ttk.Label(tab, text="Hardware Acceleration:",
              font=('', 9, 'bold')).pack(anchor=tk.W)

    device_frame = ttk.Frame(tab)
    device_frame.pack(fill=tk.X, pady=5)

    ttk.Label(device_frame, text="Device:").pack(side=tk.LEFT)
    device_combo = ttk.Combobox(
        device_frame,
        textvariable=gui.device,
        values=["auto", "cpu", "cuda", "mps"],
        state="readonly",
        width=12
    )
    device_combo.pack(side=tk.LEFT, padx=(10, 0))

    # Device descriptions
    desc_frame = ttk.Frame(tab)
    desc_frame.pack(fill=tk.X, pady=5)
    ttk.Label(
        desc_frame,
        text="auto: Auto-detect | cuda: GPU | mps: Apple Silicon | cpu: CPU only",
        foreground="gray", font=('', 8)
    ).pack(anchor=tk.W)

    # Separator
    ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

    # Threading
    ttk.Label(tab, text="CPU Threading:", font=(
        '', 9, 'bold')).pack(anchor=tk.W)

    thread_frame = ttk.Frame(tab)
    thread_frame.pack(fill=tk.X, pady=5)

    ttk.Label(thread_frame, text="Threads:").pack(side=tk.LEFT)
    ttk.Spinbox(
        thread_frame,
        from_=1,
        to=32,
        textvariable=gui.num_threads,
        width=8
    ).pack(side=tk.LEFT, padx=(10, 10))
    ttk.Label(thread_frame, text="(1-32, default: 4)",
              foreground="gray").pack(side=tk.LEFT)

    # Separator
    ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=10)

    # CUDA Options
    ttk.Label(tab, text="CUDA Options:", font=(
        '', 9, 'bold')).pack(anchor=tk.W)

    ttk.Checkbutton(tab, text="Use Flash Attention 2 (requires compatible GPU)",
                    variable=gui.use_flash_attention).pack(anchor=tk.W, pady=5)


def create_output_panel(gui, parent):
    """Create the output settings panel"""
    output_frame = ttk.LabelFrame(
        parent, text="Output Settings", padding="10")
    output_frame.pack(fill=tk.X, pady=5)

    # Output directory
    dir_frame = ttk.Frame(output_frame)
    dir_frame.pack(fill=tk.X, pady=5)

    ttk.Label(dir_frame, text="Output Directory:").pack(side=tk.LEFT)
    ttk.Entry(
        dir_frame, textvariable=gui.output_directory, width=50
    ).pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
    ttk.Button(dir_frame, text="Browse",
               command=gui.browse_output_dir).pack(side=tk.LEFT)

    # Options row
    options_frame = ttk.Frame(output_frame)
    options_frame.pack(fill=tk.X, pady=5)

    ttk.Checkbutton(options_frame, text="Create subfolder per file",
                    variable=gui.create_subfolder).pack(side=tk.LEFT, padx=(0, 15))
    ttk.Checkbutton(options_frame, text="Overwrite existing",
                    variable=gui.overwrite_files).pack(side=tk.LEFT)


def create_preview_panel(gui, parent):
    """Create the preview/log tabbed panel"""
    preview_frame = ttk.LabelFrame(
        parent, text="Preview / Log", padding="10")
    preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    # Notebook (tabbed interface)
    gui.preview_notebook = ttk.Notebook(preview_frame)
    gui.preview_notebook.pack(fill=tk.BOTH, expand=True)

    # Preview tab
    preview_tab = ttk.Frame(gui.preview_notebook)
    gui.preview_notebook.add(preview_tab, text="Preview")

    preview_scroll = ttk.Scrollbar(preview_tab)
    preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    gui.preview_text = tk.Text(
        preview_tab,
        wrap=tk.WORD,
        yscrollcommand=preview_scroll.set,
        font=('Consolas', 10),
        state=tk.DISABLED
    )
    gui.preview_text.pack(fill=tk.BOTH, expand=True)
    preview_scroll.config(command=gui.preview_text.yview)

    # Log tab
    log_tab = ttk.Frame(gui.preview_notebook)
    gui.preview_notebook.add(log_tab, text="Log")

    log_scroll = ttk.Scrollbar(log_tab)
    log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    gui.log_text = tk.Text(
        log_tab,
        wrap=tk.WORD,
        yscrollcommand=log_scroll.set,
        font=('Consolas', 9),
        state=tk.DISABLED
    )
    gui.log_text.pack(fill=tk.BOTH, expand=True)
    log_scroll.config(command=gui.log_text.yview)


def create_controls_panel(gui, parent):
    """Create the progress bar and control buttons"""
    controls_frame = ttk.Frame(parent)
    controls_frame.pack(fill=tk.X, pady=10)

    # Progress bar
    progress_frame = ttk.Frame(controls_frame)
    progress_frame.pack(fill=tk.X, pady=(0, 10))

    gui.progress_var = tk.DoubleVar(value=0)
    gui.progress_bar = ttk.Progressbar(
        progress_frame,
        variable=gui.progress_var,
        maximum=100
    )
    gui.progress_bar.pack(fill=tk.X, side=tk.LEFT,
                          expand=True, padx=(0, 10))

    gui.progress_label = ttk.Label(progress_frame, text="0%", width=5)
    gui.progress_label.pack(side=tk.LEFT)

    # Status label
    gui.status_label = ttk.Label(
        controls_frame, text="Ready", foreground="gray")
    gui.status_label.pack(fill=tk.X, pady=(0, 10))

    # Buttons
    btn_frame = ttk.Frame(controls_frame)
    btn_frame.pack()

    gui.convert_selected_btn = tk.Button(
        btn_frame,
        text="Convert Selected",
        command=gui.convert_selected,
        bg='#2563eb', fg='#ffffff',
        activebackground='#1d4ed8', activeforeground='#ffffff',
        font=('', 10, 'bold'),
        padx=16, pady=6, relief=tk.RAISED, cursor='hand2'
    )
    gui.convert_selected_btn.pack(side=tk.LEFT, padx=5)

    gui.convert_all_btn = tk.Button(
        btn_frame,
        text="Convert All",
        command=gui.convert_all,
        bg='#16a34a', fg='#ffffff',
        activebackground='#15803d', activeforeground='#ffffff',
        font=('', 10, 'bold'),
        padx=16, pady=6, relief=tk.RAISED, cursor='hand2'
    )
    gui.convert_all_btn.pack(side=tk.LEFT, padx=5)

    gui.cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=gui.cancel_conversion,
        state=tk.DISABLED,
        bg='#dc2626', fg='#ffffff',
        activebackground='#b91c1c', activeforeground='#ffffff',
        font=('', 10),
        padx=16, pady=6, relief=tk.RAISED, cursor='hand2',
        disabledforeground='#999999'
    )
    gui.cancel_btn.pack(side=tk.LEFT, padx=5)
