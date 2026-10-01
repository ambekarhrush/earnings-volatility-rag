from __future__ import annotations

import hashlib
import os
from datetime import date
from io import BytesIO
from pathlib import Path

from app.desk_models import Evidence, Opinion, OpinionClaim, ResearchPack
from app.market import DataUnavailable

DATA = Path(__file__).parent / "data"


def research_pack(ticker: str) -> ResearchPack:
    path = DATA / f"{ticker}-research.json"
    if path.exists():
        return ResearchPack.model_validate_json(path.read_text())
    return ResearchPack(
        ticker=ticker,
        company=ticker,
        evidence=[],
        editorial=Opinion(
            headline="Research evidence needed before forming a company view.",
            stance="insufficient_data",
            confidence="low",
            rationale=[
                OpinionClaim(
                    text="No curated issuer pack is loaded for this ticker.",
                    evidence_ids=["SYSTEM-COVERAGE"],
                )
            ],
            counterargument="Option prices alone cannot establish a company thesis.",
            invalidation="Add verified company evidence and reassess.",
            questions=["What changed in guidance?", "What outcome is already priced?"],
        ),
    )


def parse_document(content: bytes, filename: str, published: date) -> Evidence:
    if not content or len(content) > 8 * 1024 * 1024:
        raise ValueError("Supply a non-empty document under 8 MB.")
    suffix = Path(filename).suffix.lower()
    digest = hashlib.sha256(content).hexdigest()
    if suffix in (".md", ".txt"):
        text = content.decode("utf-8")
    elif suffix == ".pdf":
        try:
            from docling.datamodel.base_models import DocumentStream, InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except ImportError as exc:
            raise DataUnavailable(
                "Install the documents extra to enable Docling PDF parsing."
            ) from exc
        options = PdfPipelineOptions(do_ocr=False)
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        try:
            text = converter.convert(
                DocumentStream(name="upload.pdf", stream=BytesIO(content))
            ).document.export_to_markdown()
        except Exception as exc:
            raise DataUnavailable(
                "Docling could not extract this PDF. Check file validity and model-asset availability."
            ) from exc
    else:
        raise ValueError("Use PDF, Markdown or UTF-8 text.")
    if not text.strip():
        raise ValueError(
            "No readable text extracted. Image-only PDFs need an OCR-enabled pipeline."
        )
    return Evidence(
        id=f"DOC-{digest[:12]}",
        title=Path(filename).name[:160],
        text=text[:24000],
        source="User-uploaded document; publication date supplied by user",
        published=published,
        kind="upload",
        sha256=digest,
    )


def latest_filing(ticker: str) -> Evidence:
    identity = os.getenv("EDGAR_IDENTITY", "").strip()
    if not identity:
        raise DataUnavailable("Set EDGAR_IDENTITY to your contact identity before SEC requests.")
    from edgar import Company, set_identity

    set_identity(identity)
    try:
        filing = Company(ticker).get_filings(form=["10-Q", "10-K"]).latest()
        if filing is None:
            raise DataUnavailable("No 10-Q or 10-K found for this ticker.")
        content = filing.markdown()
        # Select passages near relevant terms rather than sending only the cover-page prefix.
        lowered = content.lower()
        passages = []
        for term in ("gross margin", "net sales", "revenue", "outlook", "risk factors"):
            start = 0
            for _ in range(2):
                at = lowered.find(term, start)
                if at < 0:
                    break
                passages.append(content[max(0, at - 250) : at + 1800])
                start = at + 1800
        excerpt = "\n\n[Excerpt]\n\n".join(passages) or content[:12000]
        return Evidence(
            id=f"SEC-{filing.accession_no}",
            title=f"{ticker} {filing.form}",
            text=excerpt[:24000],
            source="SEC EDGAR via EdgarTools; selected excerpts",
            published=filing.filing_date,
            url=filing.document.url,
            kind="filing",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )
    except DataUnavailable:
        raise
    except Exception as exc:
        raise DataUnavailable(
            "SEC retrieval failed. Check identity, ticker and network; retry later."
        ) from exc
