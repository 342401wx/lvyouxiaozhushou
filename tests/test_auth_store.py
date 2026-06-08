from education_qa.auth_store import AuthStore, summarize_plan, validate_password, validate_username


def test_auth_validation_requires_alnum_with_min_lengths() -> None:
    assert validate_username("abc123") is None
    assert validate_password("abc12345") is None
    assert validate_username("abcdef") is not None
    assert validate_username("ab12") is not None
    assert validate_password("abcdefgh") is not None
    assert validate_password("abc123") is not None


def test_memory_is_scoped_by_user(tmp_path) -> None:
    store = AuthStore(tmp_path / "auth.sqlite")
    user_a, error_a = store.register("user001", "pass1234")
    user_b, error_b = store.register("user002", "pass1234")

    assert error_a is None
    assert error_b is None
    assert user_a is not None
    assert user_b is not None

    store.add_memory(user_a["id"], "plan", "成都攻略", "A 的攻略", {"city": "成都"})
    store.add_memory(user_b["id"], "plan", "铜陵攻略", "B 的攻略", {"city": "铜陵"})

    memories_a = store.list_memories(user_a["id"])
    memories_b = store.list_memories(user_b["id"])

    assert [item["title"] for item in memories_a] == ["成都攻略"]
    assert [item["title"] for item in memories_b] == ["铜陵攻略"]


def test_summarize_plan_omits_unscheduled_backup_stops() -> None:
    _, summary = summarize_plan(
        {
            "city": "铜陵",
            "days_count": 1,
            "budget": {"total": 538},
            "days": [
                {
                    "stops": [
                        {"name": "铜陵动物园", "scheduled": True},
                        {"name": "铜官山", "scheduled": True},
                        {"name": "天井湖公园", "scheduled": False},
                    ]
                }
            ],
        }
    )

    assert "铜陵动物园、铜官山" in summary
    assert "天井湖公园" not in summary
