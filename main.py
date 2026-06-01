"""
Invoice Extractor Pro
Kivy-based Android app for OCR extraction of Asian Paints invoices.
"""

import os
import re
import csv
import tempfile
import threading
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.progressbar import ProgressBar
from kivy.properties import StringProperty, ListProperty
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, Rectangle

# ---------------------------------------------------------------------------
# Optional dependency flags
# ---------------------------------------------------------------------------
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


# ---------------------------------------------------------------------------
# Column layout — single source of truth for header + row widths
# ---------------------------------------------------------------------------
COLUMNS = [
    # (header_label, data_field,   width)
    ('S.No',     's_no',         55),
    ('Material', 'material_no', 110),
    ('Item Name','item_name',   195),
    ('HSN',      'hsn',          75),
    ('Qty',      'qty',          55),
    ('Unit',     'unit',         60),
    ('Price',    'price',        80),
    ('GST',      'gst',          80),
    ('Rate',     'gst_rate',     60),
    ('Amount',   'amount',       90),
]


# ---------------------------------------------------------------------------
# Reusable widgets
# ---------------------------------------------------------------------------

class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0.2, 0.6, 0.9, 1)
        self.color = (1, 1, 1, 1)
        self.font_size = '15sp'
        self.size_hint_y = None
        self.height = 50


class InvoiceRow(BoxLayout):
    """One data row in the results grid."""

    def __init__(self, item_data, row_index=0, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 40
        self.padding = [5, 2]

        # Alternate row background
        bg_color = (0.93, 0.96, 1.0, 1) if row_index % 2 == 0 else (1, 1, 1, 1)
        with self.canvas.before:
            Color(*bg_color)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_rect, size=self._sync_rect)

        for _, field, width in COLUMNS:
            value = item_data.get(field, '')
            self.add_widget(Label(
                text=str(value),
                size_hint_x=None,
                width=width,
                font_size='12sp',
                color=(0.1, 0.1, 0.1, 1),
            ))

    def _sync_rect(self, instance, _value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

class InvoiceExtractorApp(App):
    extracted_items = ListProperty([])
    status_text = StringProperty('Ready')

    # ------------------------------------------------------------------ build
    def build(self):
        Window.clearcolor = (0.98, 0.98, 0.98, 1)
        self.title = 'Invoice Extractor Pro'
        self.selected_files = []

        root = BoxLayout(orientation='vertical', padding=10, spacing=8)
        root.add_widget(self._build_header())
        root.add_widget(self._build_button_bar())

        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=18)
        root.add_widget(self.progress)

        self.file_list_label = Label(
            text='No files selected',
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None,
            height=28,
        )
        root.add_widget(self.file_list_label)

        root.add_widget(self._build_column_header())

        scroll = ScrollView()
        self.results_grid = GridLayout(cols=1, spacing=2, size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter('height'))
        scroll.add_widget(self.results_grid)
        root.add_widget(scroll)

        self.summary_label = Label(
            text='Total Items: 0  |  Total Amount: Rs. 0.00',
            font_size='14sp',
            color=(0.1, 0.45, 0.1, 1),
            size_hint_y=None,
            height=40,
        )
        root.add_widget(self.summary_label)

        self.bind(status_text=lambda inst, val: setattr(self.status_label, 'text', val))
        return root

    def _build_header(self):
        header = BoxLayout(size_hint_y=None, height=55, spacing=10)
        header.add_widget(Label(
            text='[b]INVOICE EXTRACTOR PRO[/b]',
            markup=True,
            font_size='22sp',
            color=(0.1, 0.35, 0.7, 1),
            size_hint_x=0.7,
        ))
        self.status_label = Label(
            text=self.status_text,
            font_size='12sp',
            color=(0.5, 0.5, 0.5, 1),
            size_hint_x=0.3,
        )
        header.add_widget(self.status_label)
        return header

    def _build_button_bar(self):
        bar = GridLayout(cols=4, size_hint_y=None, height=50, spacing=5)

        pick_btn = StyledButton(text='Pick Files')
        pick_btn.bind(on_press=self.show_file_chooser)
        bar.add_widget(pick_btn)

        extract_btn = StyledButton(text='Extract', background_color=(0.2, 0.7, 0.3, 1))
        extract_btn.bind(on_press=self.start_processing)
        self.btn_process = extract_btn
        bar.add_widget(extract_btn)

        save_btn = StyledButton(text='Save CSV', background_color=(0.9, 0.5, 0.2, 1))
        save_btn.bind(on_press=self.save_csv)
        bar.add_widget(save_btn)

        clear_btn = StyledButton(text='Clear', background_color=(0.8, 0.2, 0.2, 1))
        clear_btn.bind(on_press=self.clear_all)
        bar.add_widget(clear_btn)

        return bar

    def _build_column_header(self):
        header_row = BoxLayout(size_hint_y=None, height=32, spacing=2)
        for label, _field, width in COLUMNS:
            header_row.add_widget(Label(
                text='[b]{}[/b]'.format(label),
                markup=True,
                size_hint_x=None,
                width=width,
                font_size='11sp',
                color=(0.1, 0.3, 0.6, 1),
            ))
        return header_row

    # ------------------------------------------------------------- file picker
    def show_file_chooser(self, _instance):
        start_path = '/storage/emulated/0/' if platform == 'android' else os.path.expanduser('~')
        content = BoxLayout(orientation='vertical')

        self.file_chooser = FileChooserListView(
            path=start_path,
            filters=['*.jpg', '*.jpeg', '*.png', '*.pdf', '*.bmp'],
            multiselect=True,
        )
        content.add_widget(self.file_chooser)

        btn_row = BoxLayout(size_hint_y=None, height=50, spacing=5)
        sel_btn = Button(text='Select', background_color=(0.2, 0.7, 0.3, 1))
        sel_btn.bind(on_press=self._on_file_select)
        btn_row.add_widget(sel_btn)

        can_btn = Button(text='Cancel', background_color=(0.8, 0.2, 0.2, 1))
        can_btn.bind(on_press=lambda _x: self.popup.dismiss())
        btn_row.add_widget(can_btn)

        content.add_widget(btn_row)
        self.popup = Popup(title='Select Invoice Files', content=content, size_hint=(0.9, 0.9))
        self.popup.open()

    def _on_file_select(self, _instance):
        selection = self.file_chooser.selection
        if selection:
            self.selected_files = list(selection)
            self.file_list_label.text = 'Selected: {} file(s)'.format(len(selection))
            self.status_text = '{} file(s) ready'.format(len(selection))
        self.popup.dismiss()

    # --------------------------------------------------------------- processing
    def start_processing(self, _instance):
        if not self.selected_files:
            self._popup_message('Error', 'No files selected!', (0.8, 0.2, 0.2, 1))
            return
        if not TESSERACT_AVAILABLE:
            self._popup_message('Error', 'Tesseract OCR not installed.\nSee README for setup.', (0.8, 0.2, 0.2, 1))
            return

        self.btn_process.disabled = True
        self.progress.value = 0
        self.extracted_items = []
        self.results_grid.clear_widgets()

        thread = threading.Thread(target=self._process_thread, daemon=True)
        thread.start()

    def _process_thread(self):
        total = len(self.selected_files)
        for i, filepath in enumerate(self.selected_files):
            basename = os.path.basename(filepath)
            progress_pct = (i / total) * 100
            msg = 'Processing {}/{}: {}'.format(i + 1, total, basename)
            Clock.schedule_once(lambda dt, m=msg, p=progress_pct: self._set_progress(m, p))

            try:
                items = self._process_file(filepath)
                if items:
                    Clock.schedule_once(lambda dt, data=items: self._add_items(data))
            except Exception as exc:  # pylint: disable=broad-except
                print('Error processing {}: {}'.format(filepath, exc))

        Clock.schedule_once(lambda dt: self._on_complete())

    def _set_progress(self, message, value):
        self.status_text = message
        self.progress.value = value

    def _process_file(self, filepath):
        """Convert a single invoice file to text and parse items."""
        images = self._pdf_to_images(filepath) if filepath.lower().endswith('.pdf') else [filepath]
        items = []
        for img_path in images:
            processed = self._preprocess_image(img_path)
            text = self._ocr(processed)
            file_items = self._parse_invoice(text)
            for item in file_items:
                item['source_file'] = os.path.basename(filepath)
            items.extend(file_items)
            # Clean up temp image
            if processed != img_path and os.path.exists(processed):
                try:
                    os.remove(processed)
                except OSError:
                    pass
        return items

    # --------------------------------------------------------------- PDF → image
    def _pdf_to_images(self, pdf_path):
        """Render each PDF page as a PNG inside a safe temp directory."""
        images = []
        tmp_dir = tempfile.mkdtemp(prefix='inv_pdf_')

        try:
            if PYMUPDF_AVAILABLE:
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    out = os.path.join(tmp_dir, 'page_{:04d}.png'.format(page_num))
                    pix.save(out)
                    images.append(out)
                doc.close()
            elif PDF2IMAGE_AVAILABLE:
                pages = convert_from_path(pdf_path, dpi=300, output_folder=tmp_dir)
                for i, page in enumerate(pages):
                    out = os.path.join(tmp_dir, 'page_{:04d}.png'.format(i))
                    page.save(out, 'PNG')
                    images.append(out)
        except Exception as exc:  # pylint: disable=broad-except
            print('PDF conversion error: {}'.format(exc))

        return images if images else [pdf_path]

    # ----------------------------------------------------------- image preprocessing
    def _preprocess_image(self, image_path):
        """Enhance image contrast/sharpness for better OCR accuracy."""
        if not CV2_AVAILABLE:
            return image_path
        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path

            h, w = img.shape[:2]
            if h < 1500:
                scale = 1500 / h
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            tmp_path = image_path + '_proc.png'
            cv2.imwrite(tmp_path, binary)
            return tmp_path
        except Exception as exc:  # pylint: disable=broad-except
            print('Preprocess error: {}'.format(exc))
            return image_path

    # ----------------------------------------------------------------- OCR
    def _ocr(self, image_path):
        """Return raw text from image via Tesseract."""
        if not PIL_AVAILABLE or not TESSERACT_AVAILABLE:
            return ''
        try:
            img = Image.open(image_path)
            return pytesseract.image_to_string(img, config='--oem 3 --psm 6')
        except Exception as exc:  # pylint: disable=broad-except
            print('OCR error: {}'.format(exc))
            return ''

    # ----------------------------------------------------------------- parser
    def _parse_invoice(self, text):
        """
        Parse Asian Paints invoice text.

        Expected line-item format (may span ~8 lines):
          MaterialNo  Description  HSN  Qty  Unit  Rate  Value  Taxable  Tax  Total
        """
        items = []
        lines = text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            mat_match = re.search(r'(00\d{8,9}[A-Z]?)', line)

            if mat_match:
                material_no = mat_match.group(1)
                window = ' '.join(lines[i: min(i + 8, len(lines))])

                # Description
                desc_parts = [
                    l.strip() for l in lines[i: min(i + 5, len(lines))]
                    if any(kw in l for kw in ['AP ', 'APCO', 'APEX', 'EMULSION', 'PAINT', 'STNRS'])
                ]
                description = re.sub(r'IN:\s*(?:Central|State) GST OP', '', ' '.join(desc_parts)).strip()

                # HSN (6 digits starting with 320 or 321)
                hsn_m = re.search(r'\b(32[01]\d{3})\b', window)
                hsn = hsn_m.group(1) if hsn_m else ''

                # Qty + unit
                qty_m = re.search(r'\b(\d+)\s+(CAR|DRM|PCS|LT|ML)\b', window)
                qty = qty_m.group(1) if qty_m else '1'
                unit = qty_m.group(2) if qty_m else 'CAR'

                # Rate (float before "9.00" or "INR")
                rate_m = re.search(r'(\d+\.\d{2})\s+(?:9\.00|INR)', window)
                if not rate_m:
                    rate_m = re.search(r'Rate.*?([\d.]+)', window, re.IGNORECASE)
                rate = float(rate_m.group(1)) if rate_m else 0.0

                # Last three decimals → value, taxable, total
                numbers = re.findall(r'\d+\.\d{2}', window)
                try:
                    value = float(numbers[-3]) if len(numbers) >= 3 else 0.0
                    taxable = float(numbers[-2]) if len(numbers) >= 2 else 0.0
                    total = float(numbers[-1]) if numbers else 0.0
                except (ValueError, IndexError):
                    value = taxable = total = 0.0

                gst = round(total - taxable, 2)

                items.append({
                    's_no':        len(items) + 1,
                    'material_no': material_no,
                    'item_name':   description[:60],
                    'hsn':         hsn,
                    'qty':         qty,
                    'unit':        unit,
                    'price':       rate,
                    'gst':         gst,
                    'gst_rate':    '18%',
                    'amount':      total,
                    'value':       value,
                    'taxable':     taxable,
                })
                i = min(i + 8, len(lines))
            else:
                i += 1

        return items

    # --------------------------------------------------------------- UI helpers
    def _add_items(self, items):
        for item in items:
            self.extracted_items.append(item)
            row = InvoiceRow(item, row_index=len(self.extracted_items) - 1)
            self.results_grid.add_widget(row)
        self._refresh_summary()

    def _refresh_summary(self):
        n = len(self.extracted_items)
        total = sum(item.get('amount', 0) for item in self.extracted_items)
        self.summary_label.text = 'Total Items: {}  |  Total Amount: Rs. {:,.2f}'.format(n, total)

    def _on_complete(self):
        self.btn_process.disabled = False
        self.progress.value = 100
        self.status_text = 'Done! {} item(s) extracted.'.format(len(self.extracted_items))
        self._refresh_summary()

    # ---------------------------------------------------------------- save CSV
    def save_csv(self, _instance):
        if not self.extracted_items:
            self._popup_message('Error', 'No data to save!', (0.8, 0.2, 0.2, 1))
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_dir = '/storage/emulated/0/Download' if platform == 'android' else os.path.expanduser('~')
        filename = 'Invoices_{}.csv'.format(timestamp)
        filepath = os.path.join(save_dir, filename)

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'S.No', 'Material No.', 'Item Name', 'HSN/SAC',
                    'Quantity', 'Unit', 'Price/Unit (Rs)', 'GST (Rs)',
                    'GST Rate', 'Amount (Rs)', 'Source File',
                ])
                for item in self.extracted_items:
                    writer.writerow([
                        item['s_no'], item['material_no'], item['item_name'],
                        item['hsn'], item['qty'], item['unit'], item['price'],
                        item['gst'], item['gst_rate'], item['amount'],
                        item.get('source_file', ''),
                    ])

            self.status_text = 'Saved: {}'.format(filename)
            self._popup_message('Saved', 'CSV saved to:\n{}'.format(filepath), (0.2, 0.6, 0.2, 1))

        except OSError as exc:
            self._popup_message('Error', 'Save failed:\n{}'.format(exc), (0.8, 0.2, 0.2, 1))

    # ------------------------------------------------------------------ clear
    def clear_all(self, _instance):
        self.extracted_items = []
        self.selected_files = []
        self.results_grid.clear_widgets()
        self.file_list_label.text = 'No files selected'
        self.summary_label.text = 'Total Items: 0  |  Total Amount: Rs. 0.00'
        self.progress.value = 0
        self.status_text = 'Ready'

    # ----------------------------------------------------------------- popups
    def _popup_message(self, title, message, text_color):
        popup = Popup(
            title=title,
            content=Label(text=message, color=text_color),
            size_hint=(0.8, 0.3),
        )
        popup.open()


if __name__ == '__main__':
    InvoiceExtractorApp().run()
