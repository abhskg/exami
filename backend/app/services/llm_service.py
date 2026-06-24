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
                model_name = settings.LLM_MODEL or "gemini-3.1-flash-lite"
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
                    config=types.EmbedContentConfig(
                        output_dimensionality=settings.EMBEDDING_DIMENSION
                    ),
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


def generate_search_grounding(query: str, syllabus: str) -> Optional[str]:
    """
    Use Gemini Search Grounding (Google Search tool) to research a topic.
    Returns markdown text if successful, or None if provider is not Gemini
    or if the call fails / key is missing.
    """
    provider = settings.LLM_PROVIDER.lower().strip()
    has_gemini_key = (
        settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here"
    )

    if provider != "gemini" or not has_gemini_key or settings.APP_ENV == "test":
        return None

    try:
        logger.info(f"Using Gemini Google Search grounding for topic: '{query}'")
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        model_name = settings.LLM_MODEL or "gemini-2.5-flash"

        prompt = f"""You are a research agent. Perform Google Search as needed to get up-to-date and accurate details.
Write a detailed, informative summary/explanation of the following topic:
Topic: {query}
Syllabus context: {syllabus}

Structure the explanation clearly with headings, explanations, and code or examples if relevant.
Format the output strictly as clear, clean Markdown text. Do not return conversational prefixes or postfaces.
"""
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        if response.text:
            return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini search grounding failed for '{query}': {e}")

    return None


def synthesize_search_results(title: str, syllabus: str, query_data: dict[str, str]) -> str:
    """
    Synthesize raw search results into a clean, comprehensive study guide.
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

    # Construct the synthesis prompt
    sources_text = ""
    for query, text in query_data.items():
        sources_text += f"\n--- Query Topic: {query} ---\n{text[:5000]}\n"

    prompt = f"""You are an expert curriculum designer and educator.
Your task is to synthesize the retrieved raw web search data into a comprehensive, cohesive, and detailed study guide/textbook chapter.

Title: {title}
Syllabus / Learning Objectives:
{syllabus}

Retrieved Source Material:
{sources_text}

Instructions:
1. Synthesize the source material into a detailed explanation of the topics.
2. Structure the document clearly using Markdown headings (e.g., # for Title, ## for sections, ### for sub-sections).
3. Provide formal definitions, theoretical frameworks, step-by-step explanations, code examples (if applicable), and real-world applications.
4. Ensure the content directly addresses the learning objectives listed in the syllabus.
5. Maintain a professional, educational, and clean tone.
6. Return ONLY the final compiled markdown document. Do not include conversational prefaces or postfaces.
"""

    if is_mock:
        logger.warning("Using mock synthesis for web search.")
        topics_list = "\n".join(
            f"- **{q}**: Explanations and theoretical context for {q}." for q in query_data.keys()
        )
        return f"""# {title} (Mock Synthesized Guide)

## Introduction
This is a mock study guide compiled for the syllabus: {syllabus}.

## Key Topics
{topics_list}

## Conclusion
This concludes the mock syllabus study guide.
"""

    try:
        if provider == "gemini":
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            model_name = settings.LLM_MODEL or "gemini-3.1-flash-lite"
            response = client.models.generate_content(model=model_name, contents=prompt)
            return response.text.strip()
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
                        "content": "You are a professional educational compiler. Output clean markdown content only.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content.strip()
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    except Exception as e:
        logger.error(f"Failed to synthesize search results: {e}")
        # Fallback to simple concatenation if LLM fails
        fallback_content = f"# {title}\n\n## Syllabus\n{syllabus}\n\n"
        for q, text in query_data.items():
            fallback_content += f"## Topic: {q}\n\n{text[:3000]}\n\n"
        return fallback_content
