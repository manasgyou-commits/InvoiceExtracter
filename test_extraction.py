"""
test_extraction.py — Quick OCR smoke-test on a single invoice image.
Usage:
    python test_extraction.py path/to/invoice.jpg
"""

import sys


def main():
    test_image = sys.argv[1] if len(sys.argv) > 1 else 'test_invoice.jpg'

    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        print('Missing dependency: {}'.format(exc))
        print('Install with: pip install Pillow pytesseract')
        sys.exit(1)

    print('Testing OCR on: {}'.format(test_image))
    try:
        img = Image.open(test_image)
    except FileNotFoundError:
        print('File not found: {}'.format(test_image))
        sys.exit(1)

    text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')

    divider = '=' * 50
    print('\n{}\nEXTRACTED TEXT\n{}\n{}\n{}'.format(divider, divider, text, divider))


if __name__ == '__main__':
    main()
