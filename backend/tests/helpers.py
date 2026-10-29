import io

from pypdf import PdfReader, PdfWriter


def generate_sample_pdf(pages_text: list[str]) -> bytes:
    """
    Generates a valid PDF with arbitrary text on each page.
    """
    writer = PdfWriter()

    for text in pages_text:
        # Create a single page raw PDF
        escaped_text = text.replace("(", "\\(").replace(")", "\\)")
        raw = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >> endobj
4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
5 0 obj << /Length {len(escaped_text) + 40} >>
stream
BT
/F1 12 Tf
72 712 Td
({escaped_text}) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000057 00000 n 
0000000114 00000 n 
0000000237 00000 n 
0000000314 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
420
%%EOF""".encode("latin1")

        reader = PdfReader(io.BytesIO(raw))
        writer.add_page(reader.pages[0])

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def generate_blank_pdf(page_count: int = 1) -> bytes:
    """Generates an image-only / blank PDF with no extractable text."""
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def generate_encrypted_pdf(password: str = "secret123") -> bytes:
    """Generates a password-protected PDF."""
    pdf_bytes = generate_sample_pdf(["Confidential text"])
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
