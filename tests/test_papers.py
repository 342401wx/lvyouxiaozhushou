from education_qa.papers import clean_pdf_text, split_text


def test_clean_pdf_text_removes_noise_lines() -> None:
    text = "中文摘要\n⸮⸮⸮⸮⸮⸮⸮⸮\n†\n驾驶行为检测系统"
    assert clean_pdf_text(text) == "中文摘要\n驾驶行为检测系统"


def test_split_text_creates_overlapped_chunks() -> None:
    text = "\n".join([f"段落{i} 驾驶行为检测" for i in range(20)])
    chunks = split_text(text, max_chars=80, overlap=10)
    assert len(chunks) > 1
    assert "驾驶行为检测" in chunks[0]
