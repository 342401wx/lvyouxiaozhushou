from __future__ import annotations

import re
import zlib
from pathlib import Path


def _stream_from_object(body: bytes) -> bytes | None:
    match = re.search(rb"stream\r?\n(.*?)endstream", body, re.S)
    if not match:
        return None

    raw = match.group(1).strip(b"\r\n")
    if b"/FlateDecode" not in body:
        return raw

    try:
        return zlib.decompress(raw)
    except zlib.error:
        return None


def _iter_object_streams(data: bytes) -> list[bytes]:
    streams: list[bytes] = []
    for match in re.finditer(rb"(\d+)\s+0\s+obj(.*?)endobj", data, re.S):
        stream = _stream_from_object(match.group(2))
        if stream is not None:
            streams.append(stream)
    return streams


def _decode_unicode_hex(value: str) -> str:
    try:
        return bytes.fromhex(value).decode("utf-16-be")
    except Exception:
        return ""


def _parse_cmap(stream: bytes) -> dict[str, str]:
    text = stream.decode("latin1", errors="ignore")
    mapping: dict[str, str] = {}

    for block in re.findall(r"beginbfchar\s*(.*?)\s*endbfchar", text, re.S):
        for source, target in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            decoded = _decode_unicode_hex(target)
            if decoded:
                mapping[source.upper()] = decoded

    for block in re.findall(r"beginbfrange\s*(.*?)\s*endbfrange", text, re.S):
        for start, end, target in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
            block,
        ):
            start_code = int(start, 16)
            end_code = int(end, 16)
            target_code = int(target, 16)
            width = len(start)
            for code in range(start_code, end_code + 1):
                mapping[f"{code:0{width}X}"] = chr(target_code + code - start_code)

        for start, end, array in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]",
            block,
            re.S,
        ):
            start_code = int(start, 16)
            end_code = int(end, 16)
            targets = re.findall(r"<([0-9A-Fa-f]+)>", array)
            width = len(start)
            for offset, target in enumerate(targets[: end_code - start_code + 1]):
                decoded = _decode_unicode_hex(target)
                if decoded:
                    mapping[f"{start_code + offset:0{width}X}"] = decoded

    return mapping


def _build_cmap(streams: list[bytes]) -> dict[str, str]:
    cmap: dict[str, str] = {}
    for stream in streams:
        if b"begincmap" in stream:
            cmap.update(_parse_cmap(stream))
    return cmap


def _decode_pdf_hex(value: str, cmap: dict[str, str]) -> str:
    cleaned = re.sub(r"\s+", "", value.upper())
    chars: list[str] = []
    for index in range(0, len(cleaned), 4):
        code = cleaned[index : index + 4]
        if len(code) < 4:
            continue
        if code in cmap:
            chars.append(cmap[code])
            continue
        decoded = _decode_unicode_hex(code)
        if decoded:
            chars.append(decoded)
    return "".join(chars)


def _decode_literal(value: bytes) -> str:
    output = bytearray()
    index = 0
    escapes = {
        ord("n"): ord("\n"),
        ord("r"): ord("\r"),
        ord("t"): ord("\t"),
        ord("b"): 8,
        ord("f"): 12,
        ord("("): ord("("),
        ord(")"): ord(")"),
        ord("\\"): ord("\\"),
    }
    while index < len(value):
        byte = value[index]
        if byte == ord("\\") and index + 1 < len(value):
            index += 1
            output.append(escapes.get(value[index], value[index]))
        else:
            output.append(byte)
        index += 1

    try:
        return output.decode("utf-16-be")
    except UnicodeDecodeError:
        return output.decode("latin1", errors="ignore")


def _extract_text_pieces(stream: bytes, cmap: dict[str, str]) -> list[str]:
    if b"begincmap" in stream or (b"Tj" not in stream and b"TJ" not in stream):
        return []

    text = stream.decode("latin1", errors="ignore")
    pieces: list[str] = []

    for array in re.findall(r"\[(.*?)\]\s*TJ", text, re.S):
        part = ""
        for token in re.finditer(r"<([0-9A-Fa-f\s]+)>|\((?:\\.|[^\\)])*\)", array, re.S):
            raw = token.group(0)
            if raw.startswith("<"):
                part += _decode_pdf_hex(raw[1:-1], cmap)
            else:
                part += _decode_literal(raw[1:-1].encode("latin1", errors="ignore"))
        if part.strip():
            pieces.append(part)

    for token in re.finditer(r"(<([0-9A-Fa-f\s]+)>|\((?:\\.|[^\\)])*\))\s*Tj", text, re.S):
        raw = token.group(1)
        if raw.startswith("<"):
            part = _decode_pdf_hex(raw[1:-1], cmap)
        else:
            part = _decode_literal(raw[1:-1].encode("latin1", errors="ignore"))
        if part.strip():
            pieces.append(part)

    return pieces


def extract_pdf_text(path: Path) -> str:
    data = Path(path).read_bytes()
    streams = _iter_object_streams(data)
    cmap = _build_cmap(streams)
    pieces: list[str] = []
    for stream in streams:
        pieces.extend(_extract_text_pieces(stream, cmap))
    return "\n".join(pieces)


def inspect_pdf(path: Path) -> dict:
    data = Path(path).read_bytes()
    streams = _iter_object_streams(data)
    text = extract_pdf_text(path)
    return {
        "file": Path(path).name,
        "bytes": len(data),
        "page_markers": len(re.findall(rb"/Type\s*/Page\b", data)),
        "streams": len(re.findall(rb"\bstream\r?\n", data)),
        "decompressed_streams": len(streams),
        "image_objects": len(re.findall(rb"/Subtype\s*/Image", data)),
        "to_unicode_maps": len(re.findall(rb"/ToUnicode", data)),
        "text_chars": len(text),
    }
