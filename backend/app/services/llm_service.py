import json
import logging
import os
import time
from typing import Optional

from google import genai
from google.genai import types
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def pad_or_truncate(vector: list[float], target_dim: int) -> list[float]:
    """
    Ensure the vector has exactly target_dim dimensions.
    Pads with 0.0 if short, truncates if long.
    """
    current_dim = len(vector)
    if current_dim > target_dim:
        return vector[:target_dim]
    elif current_dim < target_dim:
        return vector + [0.0] * (target_dim - current_dim)
    return vector


def get_llm_client() -> OpenAI:
    """Initialize OpenAI compatible client based on provider settings."""
    if settings.LLM_PROVIDER == "lmstudio":
        return OpenAI(base_url=settings.LMSTUDIO_BASE_URL, api_key="lm-studio")
    else:  # openai
        return OpenAI(api_key=settings.OPENAI_API_KEY)


def get_embedding_client() -> OpenAI:
    """Initialize OpenAI compatible client for embeddings based on provider settings."""
    if settings.EMBEDDING_PROVIDER == "lmstudio":
        base_url = settings.EMBEDDING_BASE_URL or settings.LMSTUDIO_BASE_URL
        return OpenAI(base_url=base_url, api_key="lm-studio")
    else:  # openai
        api_key = settings.EMBEDDING_API_KEY or settings.OPENAI_API_KEY
        return OpenAI(api_key=api_key)


def generate_mcqs(prompt: str, count: int, difficulty: str) -> list[dict]:
    """
    Unified generate function supporting Gemini, OpenAI, and LMStudio.
    Automatically parses the output JSON (supporting lists or {"questions": [...]}).
    """
    provider = settings.LLM_PROVIDER.lower().strip()
    is_mock = (
        (
            provider == "gemini"
            and (
                not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key-here"
            )
        )
        or (provider == "openai" and not settings.OPENAI_API_KEY)
        or settings.APP_ENV == "test"
    )

    if is_mock:
        logger.warning(
            f"Using mock MCQ generation (provider={provider}, environment={settings.APP_ENV})."
        )
        return [
            {
                "question_text": f"Mock question generated in test/mock environment ({provider})?",
                "options": [
                    {"text": "Correct mock answer", "is_correct": True},
                    {"text": "Wrong answer A", "is_correct": False},
                    {"text": "Wrong answer B", "is_correct": False},
                    {"text": "Wrong answer C", "is_correct": False},
                ],
                "explanation": "This is a mock explanation for testing purposes.",
                "tags": ["mock", "test"],
                "difficulty": difficulty if difficulty != "mixed" else "medium",
            }
        ]

    # Max retries loop for API calls (rate limits, network glitches)
    max_retries = 5
    initial_delay = 2.0
    backoff_factor = 2.0
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            if provider == "gemini":
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                model_name = settings.LLM_MODEL or "gemini-2.0-flash"
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                raw = response.text.strip()
            elif provider in ("openai", "lmstudio"):
                client = get_llm_client()
                model_name = settings.LLM_MODEL
                if not model_name:
                    model_name = "gpt-4o-mini" if provider == "openai" else "local-model"

                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert exam question generator. You must output ONLY a valid JSON object "
                                "conforming to the requested format. Do not write any explanations or markdown blocks "
                                "outside the JSON."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content.strip()
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")

            parsed = json.loads(raw)
            # Accept either a bare list or {"questions": [...]}
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "questions" in parsed:
                return parsed["questions"]
            logger.error(f"Unexpected JSON structure from {provider}: {type(parsed)}")
            return []

        except Exception as e:
            err_msg = str(e)
            is_rate_limited = (
                "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Rate limit" in err_msg
            )
            if is_rate_limited and attempt < max_retries - 1:
                logger.warning(
                    f"{provider.upper()} API rate limited. Retrying in {delay}s "
                    f"(attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"{provider.upper()} API call failed: {e}")
                if settings.APP_ENV == "local" or settings.DEBUG:
                    # Return fallback in debug/local to avoid breaking the developer loop
                    return [
                        {
                            "question_text": f"Fallback question (API error: {str(e)[:60]})",
                            "options": [
                                {"text": "Option A (correct)", "is_correct": True},
                                {"text": "Option B", "is_correct": False},
                                {"text": "Option C", "is_correct": False},
                                {"text": "Option D", "is_correct": False},
                            ],
                            "explanation": "API call failed; this is a fallback MCQ.",
                            "tags": ["fallback"],
                            "difficulty": "medium",
                        }
                    ]
                raise e


def embed_text(texts: list[str]) -> list[list[float]]:
    """
    Unified embedding generator. Automatically aligns return dimensions with settings.EMBEDDING_DIMENSION (768).
    """
    provider = settings.EMBEDDING_PROVIDER.lower().strip()
    is_mock = (
        provider == "mock"
        or (
            provider == "gemini"
            and (
                not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key-here"
            )
        )
        or (provider == "openai" and not settings.OPENAI_API_KEY and not settings.EMBEDDING_API_KEY)
        or settings.APP_ENV == "test"
    )

    if is_mock:
        logger.warning(
            f"Using mock embeddings (provider={provider}, environment={settings.APP_ENV})."
        )
        return [[0.1 * (idx % 10)] * settings.EMBEDDING_DIMENSION for idx in range(len(texts))]

    max_retries = 5
    initial_delay = 2.0
    backoff_factor = 2.0
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            if provider == "gemini":
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                model_name = settings.EMBEDDING_MODEL or "gemini-embedding-001"
                response = client.models.embed_content(
                    model=model_name,
                    contents=texts,
                    config=types.EmbedContentConfig(output_dimensionality=settings.EMBEDDING_DIMENSION),
                )
                embeddings = [emb.values for emb in response.embeddings]
            elif provider in ("openai", "lmstudio"):
                client = get_embedding_client()
                model_name = settings.EMBEDDING_MODEL
                if not model_name:
                    model_name = "text-embedding-3-small" if provider == "openai" else "local-model"

                kwargs = {"input": texts, "model": model_name}
                # Check if we can enforce 768 dimensions for text-embedding-3 models
                if provider == "openai" and "text-embedding-3" in model_name:
                    kwargs["dimensions"] = settings.EMBEDDING_DIMENSION

                response = client.embeddings.create(**kwargs)
                embeddings = [item.embedding for item in response.data]
            else:
                raise ValueError(f"Unsupported embedding provider: {provider}")

            # Ensure all returned vectors strictly match settings.EMBEDDING_DIMENSION
            aligned_embeddings = [
                pad_or_truncate(emb, settings.EMBEDDING_DIMENSION) for emb in embeddings
            ]
            return aligned_embeddings

        except Exception as e:
            err_msg = str(e)
            is_rate_limited = (
                "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Rate limit" in err_msg
            )
            if is_rate_limited and attempt < max_retries - 1:
                logger.warning(
                    f"Embedding API rate limited ({provider}). Retrying in {delay}s "
                    f"(attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"Embedding generation failed ({provider}): {e}")
                if settings.APP_ENV == "local" or settings.DEBUG:
                    return [
                        [0.1 * (idx % 10)] * settings.EMBEDDING_DIMENSION
                        for idx in range(len(texts))
                    ]
                raise e
