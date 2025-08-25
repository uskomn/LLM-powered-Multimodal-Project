from PyPDF2 import PdfReader
import docx

ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(filepath, ext):
    """根据扩展名解析文件内容"""
    text = ""
    if ext == "txt":
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    elif ext == "pdf":
        reader = PdfReader(filepath)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    elif ext == "docx":
        doc = docx.Document(filepath)
        text = "\n".join([para.text for para in doc.paragraphs])
    return text