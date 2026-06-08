import zipfile

from education_qa.hotel_reviews import load_hotel_review_insights


def test_hotel_review_insights_include_detail_examples(tmp_path):
    csv_text = "\n".join(
        [
            "Review,Rating",
            '"location excellent walking distance shopping clean comfortable bed friendly staff",5',
            '"noisy hallway doors parking fee expensive dirty room",2',
            '"helpful desk service clean bathroom",4',
        ]
    )
    zip_path = tmp_path / "hotel_reviews.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("reviews.csv", csv_text)

    insights = load_hotel_review_insights(zip_path)

    assert insights["available"] is True
    assert "平均评分" not in insights["summary"]
    assert insights["detail_sections"]
    assert insights["booking_tips"]
    assert any(section["examples"] for section in insights["detail_sections"])
    assert any("excerpt" in example for section in insights["detail_sections"] for example in section["examples"])
