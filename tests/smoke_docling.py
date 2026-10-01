"""Optional integration smoke: tiny in-memory PDF, no provider credentials.

Run: uv run --extra documents python -m tests.smoke_docling
The first run may download Docling's model assets. Not part of lightweight CI.
"""

from datetime import date

from app.research import parse_document


def sample_pdf():
    text = b"BT /F1 16 Tf 72 720 Td (Earnings evidence parser smoke test) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(text)).encode() + b" >>\nstream\n" + text + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += str(number).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 6\n0000000000 65535 f \n"
    pdf += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    pdf += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF"
    return pdf


if __name__ == "__main__":
    result = parse_document(sample_pdf(), "parser-smoke.pdf", date(2026, 1, 1))
    assert "Earnings evidence parser smoke test" in result.text
    print("Docling PDF extraction verified; source hash:", result.sha256)
