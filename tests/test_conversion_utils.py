"""
Unit tests for conversion_utils.

Uses the stdlib unittest framework so it can be run with no extra
dependencies:  python -m unittest discover -s tests
"""
import unittest

import conversion_utils as cu


class FakeDocument:
    """Minimal stand-in for a docling document for export tests."""

    def __init__(self, markdown):
        self._markdown = markdown

    def export_to_markdown(self):
        return self._markdown

    def export_to_html(self):
        return f"<html>{self._markdown}</html>"

    def export_to_dict(self):
        return {"text": self._markdown}

    def export_to_doctags(self):
        return f"<doctags>{self._markdown}</doctags>"


class FakeResult:
    """Stand-in for a docling ConversionResult."""

    def __init__(self, markdown):
        self.document = FakeDocument(markdown)


class GetOutputExtensionTests(unittest.TestCase):
    def test_known_formats(self):
        self.assertEqual(cu.get_output_extension("Markdown"), ".md")
        self.assertEqual(cu.get_output_extension("HTML"), ".html")
        self.assertEqual(cu.get_output_extension("JSON"), ".json")
        self.assertEqual(cu.get_output_extension("DocTags"), ".doctags")
        self.assertEqual(cu.get_output_extension("Text"), ".txt")

    def test_unknown_format_falls_back_to_txt(self):
        self.assertEqual(cu.get_output_extension("Nonsense"), ".txt")


class ExportContentTests(unittest.TestCase):
    def test_markdown_passthrough(self):
        result = FakeResult("# Title\n\nBody")
        self.assertEqual(cu.export_content(result, "Markdown"), "# Title\n\nBody")

    def test_json_is_valid_and_indented(self):
        import json
        result = FakeResult("hello")
        out = cu.export_content(result, "JSON")
        self.assertEqual(json.loads(out), {"text": "hello"})

    def test_text_strips_markdown_formatting(self):
        md = "# Heading\n\n**bold** and *italic* with [link](http://x) and ![img](y.png)"
        out = cu.export_content(FakeResult(md), "Text")
        self.assertNotIn("#", out)
        self.assertNotIn("**", out)
        self.assertNotIn("![", out)
        self.assertIn("bold", out)
        self.assertIn("italic", out)
        self.assertIn("link", out)
        self.assertNotIn("http://x", out)

    def test_unknown_format_falls_back_to_markdown(self):
        result = FakeResult("# Title")
        self.assertEqual(cu.export_content(result, "Nonsense"), "# Title")


@unittest.skipUnless(cu.DOCLING_AVAILABLE, "docling not installed")
class BuildConverterTests(unittest.TestCase):
    base = {"device": "cpu", "num_threads": 4}

    def test_standard_pipeline_registers_pdf_and_image(self):
        from docling.datamodel.base_models import InputFormat

        converter, name = cu.build_converter({
            **self.base,
            "pipeline_type": "Standard",
            "enable_ocr": False,
            "do_table_structure": False,
        })
        self.assertEqual(name, "Standard")

        # The configured (non-default) options must reach both PDF and images.
        pdf_opts = converter.format_to_options[InputFormat.PDF].pipeline_options
        img_opts = converter.format_to_options[InputFormat.IMAGE].pipeline_options
        self.assertFalse(pdf_opts.do_ocr)
        self.assertFalse(img_opts.do_ocr)
        self.assertIs(pdf_opts, img_opts)

    @unittest.skipUnless(cu.VLM_AVAILABLE, "VLM pipeline not available")
    def test_vlm_pipeline_constructs(self):
        for model in ("granite_docling", "smolvlm"):
            converter, name = cu.build_converter({
                **self.base,
                "pipeline_type": "VLM",
                "vlm_model": model,
            })
            self.assertEqual(name, "VLM")
            self.assertIsNotNone(converter)

    @unittest.skipUnless(cu.ASR_AVAILABLE, "ASR pipeline not available")
    def test_asr_pipeline_constructs(self):
        converter, name = cu.build_converter({**self.base, "pipeline_type": "ASR"})
        self.assertEqual(name, "ASR")
        self.assertIsNotNone(converter)


@unittest.skipUnless(cu.DOCLING_AVAILABLE, "docling not installed")
class BuildPipelineOptionsTests(unittest.TestCase):
    def test_settings_propagate(self):
        opts = cu.build_pipeline_options({
            "enable_ocr": False,
            "do_table_structure": False,
            "table_mode": "Fast",
            "device": "cpu",
            "num_threads": 2,
        })
        self.assertFalse(opts.do_ocr)
        self.assertFalse(opts.do_table_structure)

    def test_table_mode_accurate_vs_fast(self):
        from docling.datamodel.pipeline_options import TableFormerMode

        fast = cu.build_pipeline_options({"table_mode": "Fast", "device": "cpu"})
        accurate = cu.build_pipeline_options({"table_mode": "Accurate", "device": "cpu"})
        self.assertEqual(fast.table_structure_options.mode, TableFormerMode.FAST)
        self.assertEqual(accurate.table_structure_options.mode, TableFormerMode.ACCURATE)

    @unittest.skipUnless(cu.PICTURE_DESCRIPTION_AVAILABLE, "presets unavailable")
    def test_picture_description_follows_vlm_model(self):
        granite = cu.build_pipeline_options({
            "do_picture_description": True,
            "vlm_model": "granite_docling",
            "device": "cpu",
        })
        smol = cu.build_pipeline_options({
            "do_picture_description": True,
            "vlm_model": "smolvlm",
            "device": "cpu",
        })
        self.assertIs(
            granite.picture_description_options, cu.granite_picture_description)
        self.assertIs(
            smol.picture_description_options, cu.smolvlm_picture_description)


if __name__ == "__main__":
    unittest.main()
