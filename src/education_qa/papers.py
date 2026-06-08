from __future__ import annotations

import json
import re
from pathlib import Path

from .dataset import relative_path
from .pdf_extract import extract_pdf_text, inspect_pdf
from .paths import PROJECT_ROOT

PAPER_JSONL = PROJECT_ROOT / "data" / "processed" / "papers.jsonl"
PAPER_INDEX = PROJECT_ROOT / "data" / "vectorstore" / "papers_tfidf.pkl"
PAPER_TEXT = PROJECT_ROOT / "data" / "processed" / "papers_readable.txt"

TEXT_FIXES = {
    "奯汯": "Yolo",
    "Yo汯": "Yolo",
    "Y潬o": "Yolo",
    "Y潬潶": "Yolov",
    "Y潬潶㠠": "Yolov8",
    "CB䅍": "CBAM",
    "C2f_CB䅍": "C2f_CBAM",
    "C㉦_CBAM": "C2f_CBAM",
    "C㉦": "C2f",
    "P祓楤收": "PySide6",
    "P祓i摥6": "PySide6",
    "兔hread": "QThread",
    "䝕I": "GUI",
    "䥏U": "IOU",
    "Precisi潮": "Precision",
    "Preci獩潮": "Precision",
    "P牥cisi潮": "Precision",
    "Reca汬": "Recall",
    "mAP䀰⸵": "mAP@0.5",
    "mA偀0.5": "mAP@0.5",
    "mA偀〮㔺0.95": "mAP@0.5:0.95",
    "mAP@0.㔺〮㤵": "mAP@0.5:0.95",
    "0.0ㄵ㈵": "0.01525",
    "0.0㄰ㄲ": "0.01012",
    "0.0〵㠸": "0.00588",
    "0.0㈹〱": "0.02901",
    "〮㤱㔶8": "0.9168",
    "〮㤲〱9": "0.92019",
    "〮㤳㠴0": "0.93840",
    "〮㔸㐶3": "0.58463",
    "〮㤳〹3": "0.93093",
    "〮㤳〳1": "0.93031",
    "〮㤴㐲8": "0.94428",
    "〮㘱㌶4": "0.61364",
    "㘴プ640": "640x640",
    "㘴〠×‶㐰": "640x640",
    "㌰⁆PS": "30 FPS",
    "㈶㈰": "2620",
    "㄰480": "10480",
    "㈰23": "2023",
    "2〲": "202",
}


def _mostly_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if len(stripped) <= 1:
        return True
    noise_chars = sum(1 for char in stripped if char in "⸮†.•·_-—")
    return noise_chars / max(len(stripped), 1) > 0.55


def clean_pdf_text(text: str) -> str:
    for source, target in TEXT_FIXES.items():
        text = text.replace(source, target)

    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.replace("†", " ").replace("\x00", "").strip()
        line = re.sub(r"\s+", " ", line)
        line = re.sub(r"^[ㄮ㈮㌮㐮㔮㘮]\s*", "", line)
        line = re.sub(r"(?<=\d)[〮](?=\d)", ".", line)
        if _mostly_noise(line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def split_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        if current and current_len + len(line) + 1 > max_chars:
            chunk = "\n".join(current).strip()
            if chunk:
                chunks.append(chunk)
            tail = chunk[-overlap:] if overlap > 0 else ""
            current = [tail, line] if tail else [line]
            current_len = sum(len(item) for item in current)
        else:
            current.append(line)
            current_len += len(line) + 1

    if current:
        chunk = "\n".join(current).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _title_from_path(path: Path) -> str:
    title = path.stem
    title = re.sub(r"^\d+[-_]", "", title)
    return title


def paper_records_from_pdf(path: Path) -> list[dict]:
    raw_text = extract_pdf_text(path)
    cleaned = clean_pdf_text(raw_text)
    chunks = split_text(cleaned)
    title = _title_from_path(path)
    source = relative_path(path)
    records: list[dict] = []
    for index, chunk in enumerate(chunks, start=1):
        record = {
            "id": f"{path.stem}:{index}",
            "title": title,
            "source": source,
            "chunk_index": index,
            "content_type": "paper_chunk",
            "text": chunk,
            "document": "\n".join(
                [
                    f"论文：{title}",
                    f"来源：{source}",
                    f"片段编号：{index}",
                    "内容：",
                    chunk,
                ]
            ),
            "metadata": {
                "title": title,
                "source": source,
                "chunk_index": index,
                "content_type": "paper_chunk",
            },
        }
        records.append(record)
    return records


def prepare_papers(raw_dir: Path, output_path: Path = PAPER_JSONL) -> dict:
    pdf_paths = sorted(Path(raw_dir).glob("*.pdf"))
    records: list[dict] = []
    inspections = []
    for path in pdf_paths:
        inspections.append(inspect_pdf(path))
        records.extend(paper_records_from_pdf(path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    readable_path = output_path.with_name("papers_readable.txt")
    with readable_path.open("w", encoding="utf-8-sig") as handle:
        for record in records:
            handle.write(f"# {record['title']} - chunk {record['chunk_index']}\n")
            handle.write(f"Source: {record['source']}\n\n")
            handle.write(record["text"])
            handle.write("\n\n")

    return {
        "pdfs": len(pdf_paths),
        "chunks": len(records),
        "output": relative_path(output_path),
        "readable_text": relative_path(readable_path),
        "inspections": inspections,
    }
