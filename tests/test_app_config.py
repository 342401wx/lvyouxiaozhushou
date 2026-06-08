from education_qa.app_config import get_config
from education_qa.deepseek_client import _chat_completions_url


def test_get_config_accepts_openai_compatible_llm_aliases(tmp_path, monkeypatch) -> None:
    for key in (
        "DEEPSEEK_API_KEY",
        "LLM_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_BASE_URL",
        "LLM_BASE_URL",
        "OPENAI_BASE_URL",
        "DEEPSEEK_MODEL",
        "LLM_MODEL_ID",
        "MODEL_NAME",
        "OPENAI_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=sk-test",
                "OPENAI_BASE_URL=https://example.test/v1",
                "MODEL_NAME=deepseek-chat",
            ]
        ),
        encoding="utf-8",
    )

    config = get_config(env_path)

    assert config.has_deepseek is True
    assert config.deepseek_api_key == "sk-test"
    assert config.deepseek_base_url == "https://example.test/v1"
    assert config.deepseek_model == "deepseek-chat"


def test_chat_completions_url_accepts_root_or_v1_base_url() -> None:
    assert _chat_completions_url("https://example.test") == "https://example.test/v1/chat/completions"
    assert _chat_completions_url("https://example.test/v1") == "https://example.test/v1/chat/completions"
