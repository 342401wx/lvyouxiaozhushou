from education_qa.tourism import clean_markup, records_from_wikivoyage_page


def test_clean_markup_keeps_listing_content() -> None:
    text = """
* {{see | name=西沙群岛 | address=海南省三沙市 | lat=16.5 | long=112.3 | content=这里有海岛景观和珊瑚礁。}}
"""

    clean = clean_markup(text)

    assert "西沙群岛" in clean
    assert "海南省三沙市" in clean
    assert "海岛景观和珊瑚礁" in clean
    assert "16.5,112.3" in clean


def test_records_from_wikivoyage_page_builds_documents() -> None:
    text = """
'''三沙市'''位于中国海南省南端。

==观光==
* {{see | name=西沙群岛 | content=适合海岛观光。}}
"""

    records = records_from_wikivoyage_page(
        "三沙",
        "123",
        text,
        source="memory",
        min_chars=10,
    )

    assert records[0]["title"] == "三沙"
    assert any(record["section"] == "观光" for record in records)
    assert any("西沙群岛" in record["text"] for record in records)
