# GroqLLM cubierto con un cliente OpenAI falso (sin red, sin key real)
import types

import pytest

import app.llm as llm_mod
from app.config import CONFIG
from app.llm import crear_llm


class _Msg:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _Fn:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _Call:
    def __init__(self):
        self.id = "call-1"
        self.function = _Fn("listar_medicos", "{}")


class _Resp:
    def __init__(self, message):
        self.choices = [types.SimpleNamespace(message=message)]


class _Completions:
    def __init__(self, resp):
        self._resp = resp
        self.kw = None

    def create(self, **kw):
        self.kw = kw
        return self._resp


def _fake_openai(monkeypatch, message):
    comp = _Completions(_Resp(message))
    holder: dict = {}

    def build(**kw):
        holder.update(kw)
        return types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=comp), base_url=kw.get("base_url")
        )

    monkeypatch.setattr("openai.OpenAI", build)
    return holder, comp


def test_groq_ini_error_sin_key(monkeypatch):
    monkeypatch.setattr(CONFIG, "GROQ_API_KEY", "")
    with pytest.raises(RuntimeError):
        llm_mod.GroqLLM()


def test_groq_chat_texto(monkeypatch):
    holder, comp = _fake_openai(monkeypatch, _Msg("¿Con qué especialidad?"))
    monkeypatch.setattr(CONFIG, "GROQ_API_KEY", "fake-key")
    llm = llm_mod.GroqLLM()
    out = llm.chat([{"role": "user", "content": "hola"}], [])
    assert out.texto == "¿Con qué especialidad?"
    assert out.tool_calls == []
    assert comp.kw["model"] == CONFIG.LLM_MODEL
    assert "groq.com" in str(holder.get("base_url"))


def test_groq_chat_tool_calls(monkeypatch):
    msg = _Msg(None, [_Call()])
    _fake_openai(monkeypatch, msg)
    monkeypatch.setattr(CONFIG, "GROQ_API_KEY", "fake-key")
    llm = llm_mod.GroqLLM()
    out = llm.chat([{"role": "user", "content": "hola"}], [])
    assert out.texto is None
    assert out.tool_calls[0]["function"]["name"] == "listar_medicos"


def test_crear_llm_segun_env(monkeypatch):
    monkeypatch.setattr(CONFIG, "MOCK_LLM", True)
    assert isinstance(crear_llm(), llm_mod.MockLLM)

    monkeypatch.setattr(CONFIG, "MOCK_LLM", False)
    monkeypatch.setattr(CONFIG, "GROQ_API_KEY", "fake-key")
    _fake_openai(monkeypatch, _Msg("x"))
    assert isinstance(crear_llm(), llm_mod.GroqLLM)
