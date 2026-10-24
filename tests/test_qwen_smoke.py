import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel, Field
from backend.app.services.llm_client import (
    QwenClient,
    LLMError,
    LLMAuthError,
    LLMRateLimitError,
    LLMPaymentRequiredError,
    LLMTimeoutError,
    LLMValidationError,
    extract_json_content
)
from backend.app.services.cache_service import get_llm_cache

class SampleAnalysisSchema(BaseModel):
    summary: str = Field(description="Summary of task")
    confidence: float = Field(default=1.0)
    status: str = Field(default="ok")

def test_extract_json_content_strips_markdown():
    raw_markdown = "```json\n{\"key\": \"value\"}\n```"
    assert extract_json_content(raw_markdown) == "{\"key\": \"value\"}"

    plain = "{\"key\": \"value\"}"
    assert extract_json_content(plain) == "{\"key\": \"value\"}"

@pytest.mark.asyncio
async def test_qwen_client_structured_completion_success():
    """Verifies schema validation succeeds when valid JSON is returned."""
    client = QwenClient(api_key="test_token", model="test_model", base_url="https://mock.test/v1")

    valid_json = '{"summary": "Issue asks to update retry delay", "confidence": 0.95, "status": "ok"}'
    with patch.object(client, "_post_chat_completion", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = valid_json

        res = await client.complete_structured(
            system_prompt="Analyze this issue",
            user_prompt="Issue title: Fix timeout",
            response_model=SampleAnalysisSchema,
            use_cache=False
        )

        assert isinstance(res, SampleAnalysisSchema)
        assert res.summary == "Issue asks to update retry delay"
        assert res.confidence == 0.95
        assert res.status == "ok"
        assert mock_post.call_count == 1

@pytest.mark.asyncio
async def test_qwen_client_retry_on_malformed_json():
    """Verifies that client retries once on malformed JSON and succeeds if 2nd attempt is valid."""
    client = QwenClient(api_key="test_token", model="test_model", base_url="https://mock.test/v1")

    malformed_attempt = "I am an AI, here is your json: {summary: 'missing quotes'}"
    valid_attempt = '{"summary": "Fixed on retry", "confidence": 0.8, "status": "ok"}'

    with patch.object(client, "_post_chat_completion", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [malformed_attempt, valid_attempt]

        res = await client.complete_structured(
            system_prompt="Analyze this issue",
            user_prompt="Issue title: Fix timeout",
            response_model=SampleAnalysisSchema,
            max_retries=1,
            use_cache=False
        )

        assert res.summary == "Fixed on retry"
        assert mock_post.call_count == 2

@pytest.mark.asyncio
async def test_qwen_client_caching():
    """Verifies that identical calls return cached response without repeated network requests."""
    client = QwenClient(api_key="test_token", model="test_model", base_url="https://mock.test/v1")

    valid_json = '{"summary": "Cached result", "confidence": 1.0, "status": "ok"}'

    import uuid
    unique_user_prompt = f"Cache test prompt {uuid.uuid4()}"

    with patch.object(client, "_post_chat_completion", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = valid_json

        # Call 1: uncached -> invokes mock_post
        res1 = await client.complete_structured(
            system_prompt="System instructions for cache test",
            user_prompt=unique_user_prompt,
            response_model=SampleAnalysisSchema,
            use_cache=True
        )

        # Call 2: identical arguments -> must be served from SQLite cache
        res2 = await client.complete_structured(
            system_prompt="System instructions for cache test",
            user_prompt=unique_user_prompt,
            response_model=SampleAnalysisSchema,
            use_cache=True
        )


        assert res1.summary == "Cached result"
        assert res2.summary == "Cached result"
        assert mock_post.call_count == 1  # Only 1 network call made!

@pytest.mark.asyncio
async def test_qwen_client_error_handling():
    """Verifies error handling for missing token, 402, 429, and timeouts."""
    # 1. Missing token
    client_no_token = QwenClient(api_key="", model="test_model", base_url="https://mock.test/v1")
    with pytest.raises(LLMAuthError):
        await client_no_token.complete_structured("sys", "user", SampleAnalysisSchema, use_cache=False)

    # 2. 429 Rate limit
    import httpx
    client = QwenClient(api_key="token", model="test_model", base_url="https://mock.test/v1")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(status_code=429, text="Rate limit exceeded", request=httpx.Request("POST", "https://mock.test/v1"))
        with pytest.raises(LLMRateLimitError):
            await client.complete_structured("sys", "user", SampleAnalysisSchema, use_cache=False)

        # 3. 402 Payment required / credits exhausted
        mock_post.return_value = httpx.Response(status_code=402, text="Credits exhausted", request=httpx.Request("POST", "https://mock.test/v1"))
        with pytest.raises(LLMPaymentRequiredError):
            await client.complete_structured("sys", "user", SampleAnalysisSchema, use_cache=False)

        # 4. Timeout
        mock_post.side_effect = httpx.TimeoutException("Read timed out")
        with pytest.raises(LLMTimeoutError):
            await client.complete_structured("sys", "user", SampleAnalysisSchema, use_cache=False)
