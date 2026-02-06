import os
import pdfplumber
import docx
import openpyxl
from PIL import Image
import pytesseract

# WINDOWS için Tesseract yolu (Linux/Mac'te gerek yok)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text_from_file(file_path):
    if not os.path.exists(file_path):
        return "Dosya bulunamadı"

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".pdf":
            return extract_pdf(file_path)

        elif ext == ".docx":
            return extract_docx(file_path)

        elif ext == ".xlsx":
            return extract_excel(file_path)

        elif ext in [".png", ".jpg", ".jpeg"]:
            return extract_image(file_path)

        else:
            return "Desteklenmeyen dosya formatı"

    except Exception as e:
        return f"Hata oluştu: {str(e)}"


def extract_pdf(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_docx(path):
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_excel(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    text = ""

    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            row_text = " ".join(str(cell) for cell in row if cell is not None)
            if row_text:
                text += row_text + "\n"

    return text


def extract_image(path):
    img = Image.open(path)
    return pytesseract.image_to_string(
        img,
        lang="tur",
        config="--psm 6"
    )
