import io
import json
import re
import zipfile
from typing import Any
from xml.etree import ElementTree

from pypdf import PdfReader

from app.core.exceptions import ValidationError
from app.utils.text import validate_excerpt_in_text


def extract_transcript_text(filename: str, content: bytes) -> str:
    """
    Extracts plain text dialogue from supported transcript file formats:
    .txt, .md, .json, .pdf, .docx
    Raises ValidationError if format is unsupported or file is corrupted.
    """
    if len(content) == 0:
        raise ValidationError("Uploaded transcript file is empty")

    name = filename.lower()

    if name.endswith((".txt", ".md")):
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="replace")

    elif name.endswith(".json"):
        try:
            data = json.loads(content.decode("utf-8"))
            if isinstance(data, str):
                return data
            if isinstance(data, dict):
                if "transcript" in data and isinstance(data["transcript"], str):
                    return data["transcript"]
                if "turns" in data and isinstance(data["turns"], list):
                    lines = []
                    for turn in data["turns"]:
                        speaker = turn.get("speaker") or turn.get("role") or "Speaker"
                        text = turn.get("text") or turn.get("content") or ""
                        time = f" [{turn.get('timestamp')}]" if "timestamp" in turn else ""
                        lines.append(f"{speaker}{time}: {text}")
                    return "\n".join(lines)
            if isinstance(data, list):
                lines = []
                for turn in data:
                    if isinstance(turn, dict):
                        speaker = turn.get("speaker") or turn.get("role") or "Speaker"
                        text = turn.get("text") or turn.get("content") or ""
                        time = f" [{turn.get('timestamp')}]" if "timestamp" in turn else ""
                        lines.append(f"{speaker}{time}: {text}")
                    else:
                        lines.append(str(turn))
                return "\n".join(lines)
            return json.dumps(data, indent=2)
        except Exception as exc:
            raise ValidationError(f"Invalid JSON transcript file: {str(exc)}") from exc

    elif name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(content))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            full_text = "\n\n".join(pages_text).strip()
            if not full_text:
                raise ValidationError("PDF transcript contains no selectable digital text.")
            return full_text
        except Exception as exc:
            raise ValidationError(f"Failed to read PDF transcript: {str(exc)}") from exc

    elif name.endswith(".docx"):
        try:
            # Extract word/document.xml from docx zip container
            with zipfile.ZipFile(io.BytesIO(content)) as docx:
                xml_content = docx.read("word/document.xml")
            tree = ElementTree.fromstring(xml_content)
            # Find all w:t (text) nodes in document XML
            namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for p in tree.iterfind(".//w:p", namespaces):
                texts = [node.text for node in p.iterfind(".//w:t", namespaces) if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            return "\n".join(paragraphs)
        except Exception as exc:
            raise ValidationError(f"Failed to read DOCX transcript: {str(exc)}") from exc

    raise ValidationError(
        f"Unsupported transcript format '{filename}'. Allowed formats: .txt, .md, .json, .pdf, .docx"
    )


def validate_transcript_quote_grounding(transcript_text: str, excerpt: str) -> bool:
    """
    Strict anti-hallucination guardrail:
    Verifies that the candidate answer excerpt exists verbatim in the transcript text.
    """
    return validate_excerpt_in_text(excerpt, transcript_text)


def estimate_line_numbers(transcript_text: str, excerpt: str) -> tuple[int | None, int | None]:
    """
    Locates the 1-indexed start and end line numbers of an excerpt within the transcript text.
    """
    norm_excerpt = " ".join(excerpt.split())
    if not norm_excerpt:
        return None, None

    lines = transcript_text.splitlines()
    for idx, line in enumerate(lines, start=1):
        if norm_excerpt[:40] in " ".join(line.split()):
            # Found starting line
            return idx, idx + max(0, len(excerpt.splitlines()) - 1)

    return None, None
