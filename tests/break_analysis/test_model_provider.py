import httpx
import pytest
from langchain_core.exceptions import OutputParserException
from langchain_ollama import ChatOllama
from ollama import ResponseError

from break_analysis.model_provider import OllamaChatModelProvider

# -- chat_model ------------------------------------------------------------


def test_chat_model_returns_chat_ollama_with_configured_settings():
    provider = OllamaChatModelProvider(
        model='qwen3:14b-q4_K_M', temperature=0, base_url='http://ollama:11434'
    )

    llm = provider.chat_model()

    assert isinstance(llm, ChatOllama)
    assert llm.model == 'qwen3:14b-q4_K_M'
    assert llm.temperature == 0
    assert llm.base_url == 'http://ollama:11434'


# -- is_transient_error ----------------------------------------------------


@pytest.mark.parametrize(
    'exc',
    [
        httpx.ConnectError('connection refused'),
        httpx.ConnectTimeout('connect timed out'),
        httpx.ReadTimeout('read timed out'),
        httpx.WriteTimeout('write timed out'),
        httpx.PoolTimeout('pool timed out'),
        httpx.ReadError('connection reset'),
        httpx.WriteError('broken pipe'),
        httpx.RemoteProtocolError('server disconnected'),
        ConnectionError('Failed to connect to Ollama.'),
        ResponseError('rate limited', 429),
        ResponseError('bad gateway', 502),
        ResponseError('server busy', 503),
        ResponseError('gateway timeout', 504),
    ],
    ids=repr,
)
def test_is_transient_error_with_retryable_failure_returns_true(exc):
    assert OllamaChatModelProvider(model='qwen3').is_transient_error(exc)


@pytest.mark.parametrize(
    'exc',
    [
        ResponseError('model runner crashed', 500),
        ResponseError("model 'missing' not found", 404),
        ResponseError('invalid request', 400),
        ResponseError('error in stream'),
        httpx.UnsupportedProtocol('bad base_url scheme'),
        httpx.LocalProtocolError('invalid request'),
        httpx.ProxyError('proxy refused'),
        httpx.DecodingError('bad encoding'),
        ValueError('invalid message'),
        TypeError('unexpected argument'),
        RuntimeError('client not initialized'),
        OutputParserException('invalid tool call'),
    ],
    ids=repr,
)
def test_is_transient_error_with_non_retryable_failure_returns_false(exc):
    assert not OllamaChatModelProvider(model='qwen3').is_transient_error(exc)
