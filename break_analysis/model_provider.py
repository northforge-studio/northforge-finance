from dataclasses import dataclass
from typing import Protocol

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from ollama import ResponseError

# Status 500 is deliberately excluded: Ollama also uses it for persistent
# failures (e.g. model does not fit in memory), so retrying only delays them.
_OLLAMA_TRANSIENT_STATUS_CODES = frozenset({429, 502, 503, 504})

_OLLAMA_TRANSIENT_ERRORS = (
    # ChatOllama streams by default, so connection failures surface as raw httpx
    # errors; the non-streaming client path converts ConnectError to the builtin.
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.ReadError,
    httpx.WriteError,
    httpx.RemoteProtocolError,
    ConnectionError,
)


class ChatModelProvider(Protocol):
    def chat_model(self) -> BaseChatModel: ...

    def is_transient_error(self, exc: BaseException) -> bool: ...


@dataclass(frozen=True)
class OllamaChatModelProvider:
    model: str
    temperature: float = 0
    base_url: str | None = None

    def chat_model(self) -> ChatOllama:
        return ChatOllama(
            model=self.model, temperature=self.temperature, base_url=self.base_url
        )

    def is_transient_error(self, exc: BaseException) -> bool:
        if isinstance(exc, ResponseError):
            return exc.status_code in _OLLAMA_TRANSIENT_STATUS_CODES

        return isinstance(exc, _OLLAMA_TRANSIENT_ERRORS)
