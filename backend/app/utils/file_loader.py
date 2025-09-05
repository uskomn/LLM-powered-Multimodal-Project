import chardet
from docx import Document as DocxDocument
import PyPDF2

def read_file_content(file):
    filename = file.filename.lower()

    if filename.endswith(".txt"):
        file_bytes = file.read()
        encoding = chardet.detect(file_bytes)["encoding"] or "utf-8"
        return file_bytes.decode(encoding, errors="ignore")

    elif filename.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file)
        return "\n".join(page.extract_text() or "" for page in pdf_reader.pages)

    elif filename.endswith(".docx"):
        doc = DocxDocument(file)
        return "\n".join([para.text for para in doc.paragraphs])

    else:
        raise ValueError("Unsupported file format")
