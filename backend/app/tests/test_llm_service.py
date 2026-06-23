import pytest

from app.core.config import settings
from app.services import llm_service


def test_pad_or_truncate():
    # Test padding
    short_vec = [1.0, 2.0, 3.0]
    padded = llm_service.pad_or_truncate(short_vec, 6)
    assert padded == [1.0, 2.0, 3.0, 0.0, 0.0, 0.0]

    # Test truncating
    long_vec = [1.0, 2.0, 3.0, 4.0, 5.0]
    truncated = llm_service.pad_or_truncate(long_vec, 3)
    assert truncated == [1.0, 2.0, 3.0]

    # Test identical length
    matching_vec = [0.5] * 768
    same = llm_service.pad_or_truncate(matching_vec, 768)
    assert len(same) == 768
    assert same == matching_vec


def test_embed_text_mock_in_test_env(monkeypatch):
    # In test env settings.APP_ENV == "test", embed_text should use mock implementation
    texts = ["hello", "world"]
    embeddings = llm_service.embed_text(texts)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == settings.EMBEDDING_DIMENSION
    assert embeddings[0] == [0.1 * (0 % 10)] * settings.EMBEDDING_DIMENSION
    assert embeddings[1] == [0.1 * (1 % 10)] * settings.EMBEDDING_DIMENSION


def test_generate_mcqs_mock_in_test_env():
    # In test env generate_mcqs should use mock implementation
    questions = llm_service.generate_mcqs("dummy prompt", 5, "hard")

    assert len(questions) == 1
    q = questions[0]
    assert "Mock question generated" in q["question_text"]
    assert len(q["options"]) == 4
    assert any(opt["is_correct"] for opt in q["options"])
    assert q["difficulty"] == "hard"
