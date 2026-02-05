"""
Conversion utilities for Docling GUI
"""
import json
import re

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
    DocumentConverter = None
    PdfFormatOption = None
    InputFormat = None
    PdfPipelineOptions = None
    TableFormerMode = None
    AcceleratorOptions = None

# Try to import VLM pipeline
try:
    from docling.datamodel.pipeline_options import VlmPipelineOptions
    VLM_AVAILABLE = True
except ImportError:
    VLM_AVAILABLE = False
    VlmPipelineOptions = None

# Try to import ASR pipeline
try:
    from docling.datamodel.pipeline_options import AsrPipelineOptions
    ASR_AVAILABLE = True
except ImportError:
    ASR_AVAILABLE = False
    AsrPipelineOptions = None

# Try to import OCR options
try:
    from docling.datamodel.pipeline_options import (
        EasyOcrOptions,
        RapidOcrOptions,
    )
    OCR_OPTIONS_AVAILABLE = True
except ImportError:
    OCR_OPTIONS_AVAILABLE = False
    EasyOcrOptions = None
    RapidOcrOptions = None

# Try to import OcrMac (macOS only)
try:
    from docling.datamodel.pipeline_options import OcrMacOptions
    OCRMAC_AVAILABLE = True
except ImportError:
    OCRMAC_AVAILABLE = False
    OcrMacOptions = None

__all__ = [
    'DOCLING_AVAILABLE',
    'OCR_OPTIONS_AVAILABLE',
    'OCRMAC_AVAILABLE',
    'VLM_AVAILABLE',
    'ASR_AVAILABLE',
    'get_output_extension',
    'export_content',
    'build_pipeline_options',
    'build_converter',
    'DocumentConverter',
    'PdfFormatOption',
    'InputFormat',
]


def get_output_extension(format_name):
    """Get file extension for output format"""
    extensions = {
        "Markdown": ".md",
        "HTML": ".html",
        "JSON": ".json",
        "DocTags": ".doctags",
        "Text": ".txt"
    }
    return extensions.get(format_name, ".txt")


def export_content(result, format_name):
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
        md = doc.export_to_markdown()
        # Strip markdown formatting: headers, bold, italic, links, images
        text = re.sub(r'^#{1,6}\s+', '', md, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'\[(.+?)\]\(.*?\)', r'\1', text)
        return text
    else:
        return doc.export_to_markdown()


def build_pipeline_options(settings):
    """
    Build pipeline options from settings dictionary.

    Expected settings keys matches the GUI attributes:
    - enable_ocr, do_table_structure, ...
    - ocr_engine, ocr_language, ...
    - device, num_threads, ...
    """
    if not DOCLING_AVAILABLE:
        return None

    # Create pipeline options (defaults match GUI init_variables)
    pipeline_options = PdfPipelineOptions(
        do_ocr=settings.get('enable_ocr', True),
        do_table_structure=settings.get('do_table_structure', True),
        do_picture_classification=settings.get(
            'do_picture_classification', True),
        do_picture_description=settings.get('do_picture_description', False),
        generate_page_images=settings.get('generate_page_images', False),
        generate_picture_images=settings.get('generate_picture_images', False),
        generate_table_images=settings.get('generate_table_images', False),
    )

    # Set optional enrichment options if available
    if hasattr(pipeline_options, 'do_formula_enrichment'):
        pipeline_options.do_formula_enrichment = settings.get(
            'do_formula_enrichment', True)
    if hasattr(pipeline_options, 'do_code_enrichment'):
        pipeline_options.do_code_enrichment = settings.get(
            'do_code_enrichment', True)

    # Table structure options
    if hasattr(pipeline_options, 'table_structure_options'):
        if settings.get('table_mode') == "Fast":
            pipeline_options.table_structure_options.mode = TableFormerMode.FAST
        else:
            pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        pipeline_options.table_structure_options.do_cell_matching = settings.get(
            'do_cell_matching', True)

    # OCR options
    if OCR_OPTIONS_AVAILABLE and settings.get('enable_ocr', False):
        ocr_engine = settings.get('ocr_engine', 'RapidOCR')
        lang = settings.get('ocr_language', 'en')
        force_full_page = settings.get('force_full_page_ocr', True)
        confidence = settings.get('ocr_confidence', 0.8)

        if ocr_engine == "EasyOCR":
            pipeline_options.ocr_options = EasyOcrOptions(
                lang=[lang],
                force_full_page_ocr=force_full_page,
                confidence_threshold=confidence
            )
        elif ocr_engine == "RapidOCR" or ocr_engine == "Auto":
            pipeline_options.ocr_options = RapidOcrOptions(
                lang=[lang],
                force_full_page_ocr=force_full_page
            )
        elif ocr_engine == "OcrMac" and OCRMAC_AVAILABLE:
            pipeline_options.ocr_options = OcrMacOptions(
                lang=lang,
                force_full_page_ocr=force_full_page
            )

    # Accelerator options
    pipeline_options.accelerator_options = AcceleratorOptions(
        device=settings.get('device', 'cpu'),
        num_threads=settings.get('num_threads', 4)
    )
    if hasattr(pipeline_options.accelerator_options, 'cuda_use_flash_attention2'):
        pipeline_options.accelerator_options.cuda_use_flash_attention2 = settings.get(
            'use_flash_attention', False)

    # Images scale
    if hasattr(pipeline_options, 'images_scale'):
        pipeline_options.images_scale = settings.get('images_scale', 1.0)

    # Document timeout
    timeout = settings.get('document_timeout', 0)
    if timeout > 0 and hasattr(pipeline_options, 'document_timeout'):
        pipeline_options.document_timeout = float(timeout)

    return pipeline_options


def build_converter(settings):
    """
    Build a DocumentConverter with proper pipeline and format options
    based on the selected pipeline type.

    Returns (converter, pipeline_name) tuple.
    """
    if not DOCLING_AVAILABLE:
        return None, "unavailable"

    pipeline_type = settings.get('pipeline_type', 'Standard')

    if pipeline_type == "VLM" and VLM_AVAILABLE:
        converter = DocumentConverter(pipeline=VlmPipelineOptions)
        return converter, "VLM"

    if pipeline_type == "ASR" and ASR_AVAILABLE:
        converter = DocumentConverter(pipeline=AsrPipelineOptions)
        return converter, "ASR"

    # Standard pipeline - apply PDF options to all supported formats
    pipeline_options = build_pipeline_options(settings)
    if pipeline_options:
        format_options = {
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options),
        }
        converter = DocumentConverter(format_options=format_options)
    else:
        converter = DocumentConverter()

    return converter, "Standard"
