import pymupdf
import pytesseract
from PIL import Image
import io

def extract_text_with_ocr(page):
    """
    Convert a PDF page to an image and extract text using OCR.
    """

    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))

    image_bytes = pixmap.tobytes("png")

    image = Image.open(io.BytesIO(image_bytes))

    text = pytesseract.image_to_string(image)

    return text.strip()