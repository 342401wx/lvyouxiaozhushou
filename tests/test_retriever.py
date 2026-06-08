from education_qa.assistant import answer_question
from education_qa.dataset import enrich_record
from education_qa.retriever import TfidfRagStore


def test_tfidf_store_retrieves_relevant_record() -> None:
    records = [
        enrich_record(
            {
                "id": "operating_system:1",
                "subject": "operating_system",
                "subject_label": "操作系统",
                "question": "关于进程和线程的区别，下列说法正确的是哪一项？",
                "options": {
                    "A": "线程拥有独立地址空间",
                    "B": "进程是资源分配的基本单位，线程是 CPU 调度的基本单位",
                    "C": "进程只能包含一个线程",
                    "D": "线程之间完全不能共享数据",
                },
                "answer": "B",
                "explanation": "进程通常拥有独立资源，线程是 CPU 调度和执行的基本单位。",
                "source": "memory",
                "row_index": 0,
            }
        ),
        enrich_record(
            {
                "id": "computer_network:1",
                "subject": "computer_network",
                "subject_label": "计算机网络",
                "question": "DNS 系统的主要作用是什么？",
                "options": {
                    "A": "把域名解析为 IP 地址",
                    "B": "给网页内容加密",
                    "C": "控制物理线路",
                    "D": "检测进程状态",
                },
                "answer": "A",
                "explanation": "DNS 提供域名到 IP 地址的解析。",
                "source": "memory",
                "row_index": 1,
            }
        ),
    ]

    store = TfidfRagStore.build(records)
    hits = store.search("进程和线程有什么区别", top_k=1)
    answer = answer_question("进程和线程有什么区别", store, top_k=1)

    assert hits[0].record["subject"] == "operating_system"
    assert "进程是资源分配的基本单位" in answer
