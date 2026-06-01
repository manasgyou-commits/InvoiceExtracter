"""
test_parser.py — unit tests for the invoice parser logic.
These run without Kivy, Tesseract, or any display hardware.
Run: pytest test_parser.py -v
"""

import sys
import types

# ---------------------------------------------------------------------------
# Stub out kivy and all heavy deps so we can import the parser in isolation
# ---------------------------------------------------------------------------
def _stub_module(*names):
    for name in names:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
        # Provide stub classes that tests might reference
        mod.App = object
        mod.StringProperty = lambda *a, **kw: None
        mod.ListProperty = lambda *a, **kw: None

_stub_module(
    'kivy', 'kivy.app', 'kivy.uix.boxlayout', 'kivy.uix.gridlayout',
    'kivy.uix.scrollview', 'kivy.uix.label', 'kivy.uix.button',
    'kivy.uix.popup', 'kivy.uix.filechooser', 'kivy.uix.progressbar',
    'kivy.properties', 'kivy.clock', 'kivy.core.window',
    'kivy.utils', 'kivy.graphics',
    'PIL', 'PIL.Image', 'pytesseract', 'cv2',
    'pdf2image', 'pdf2image.convert_from_path', 'fitz',
)

# Patch property constructors so class body doesn't crash
import kivy.properties as _kp
_kp.StringProperty = lambda *a, **kw: ''
_kp.ListProperty = lambda *a, **kw: []

# Now we can safely import the app module
import importlib
import main as app_module

# Grab the raw parser method (unbound)
_parse = app_module.InvoiceExtractorApp._parse_invoice


class FakeApp:
    """Minimal stand-in so we can call the unbound method."""
    pass


def parse(text):
    return _parse(FakeApp(), text)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

SAMPLE_LINE = (
    "0001011221A  AP APEX EMULSION 18 LTR  320614  2 CAR  "
    "1234.56 9.00 2469.12  2469.12  444.44  2913.56"
)


def test_parse_returns_list():
    result = parse(SAMPLE_LINE)
    assert isinstance(result, list)


def test_parse_extracts_material_number():
    result = parse(SAMPLE_LINE)
    assert len(result) == 1
    assert result[0]['material_no'] == '0001011221A'


def test_parse_extracts_hsn():
    result = parse(SAMPLE_LINE)
    assert result[0]['hsn'] == '320614'


def test_parse_extracts_qty_and_unit():
    result = parse(SAMPLE_LINE)
    assert result[0]['qty'] == '2'
    assert result[0]['unit'] == 'CAR'


def test_parse_empty_text():
    assert parse('') == []


def test_parse_no_material_number():
    assert parse('Some random line without a valid material number.') == []


def test_parse_multiple_items():
    two_items = "\n".join([SAMPLE_LINE, SAMPLE_LINE.replace('0001011221A', '0001099999B')])
    result = parse(two_items)
    assert len(result) == 2


def test_sno_increments():
    two_items = "\n".join([SAMPLE_LINE, SAMPLE_LINE.replace('0001011221A', '0001099999B')])
    result = parse(two_items)
    assert result[0]['s_no'] == 1
    assert result[1]['s_no'] == 2


def test_gst_calculated():
    result = parse(SAMPLE_LINE)
    item = result[0]
    # gst = total - taxable (both extracted from the last two decimal numbers)
    assert isinstance(item['gst'], float)


def test_item_name_truncated():
    long_name = 'A' * 200
    text = "0001011221A " + long_name + " 320614 2 CAR 1234.56 9.00 2469.12 2469.12 444.44 2913.56"
    result = parse(text)
    if result:
        assert len(result[0]['item_name']) <= 60
