from pathlib import Path

from education_qa.dataset import load_jsonl, prepare_dataset


def test_prepare_dataset_writes_expected_schema(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    csv_path = raw_dir / "college_programming_val.csv"
    csv_path.write_text(
        "\n".join(
            [
                "id,question,A,B,C,D,answer,explanation",
                '1,"Python 函数默认参数的作用是什么？","省略实参时使用预设值","只能传列表","禁止关键字传参","自动结束程序","A","默认参数可以简化调用。"',
            ]
        ),
        encoding="utf-8",
    )

    output = tmp_path / "processed" / "education_qa.jsonl"
    stats = prepare_dataset(raw_dir, output)
    records = load_jsonl(output)

    assert stats["records"] == 1
    assert records[0]["subject"] == "college_programming"
    assert records[0]["answer"] == "A"
    assert "document" in records[0]
    assert records[0]["metadata"]["subject_label"] == "大学编程"
