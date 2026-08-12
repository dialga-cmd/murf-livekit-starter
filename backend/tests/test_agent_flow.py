import os
import sys
from types import SimpleNamespace

import pytest

# Make backend/src importable during pytest collection.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import agent as agent_module
from agent import Assistant, _build_system_prompt
import database


@pytest.mark.asyncio
async def test_save_caller_info_requires_name() -> None:
    assistant = Assistant()
    result = await assistant.save_caller_info(
        SimpleNamespace(), "user-1", "   ", "en", "{}"
    )

    assert "need the caller's name" in result.lower()


def test_inbound_prompt_excludes_outbound_script() -> None:
    prompt = _build_system_prompt("inbound")

    assert "outbound call handling" not in prompt.lower()
    assert "calls you initiated to the user" not in prompt.lower()
    assert "say 'stop' at any time" not in prompt.lower()
    assert "just an agent" in prompt.lower()
    assert "post this on the dashboard" in prompt.lower()
    assert "professional hospital tone" in prompt.lower()
    assert "How can I assist you today?" in prompt


def test_outbound_prompt_keeps_outbound_script() -> None:
    prompt = _build_system_prompt("outbound")

    assert "medication reminder" in prompt.lower()
    assert "say 'stop' at any time" in prompt.lower()


@pytest.mark.asyncio
async def test_create_escalation_wait_requests_music_confirmation(monkeypatch) -> None:
    assistant = Assistant()
    calls = []

    def fake_create_escalation(user_id: str, summary: str, urgency: str, language: str):
        return "REQ-ABC123"

    async def fake_monitor(session, reference_id):
        return None

    class FakeSession:
        async def interrupt(self, force=False):
            return None

        def say(self, *args, **kwargs):
            class Handle:
                async def wait_for_playout(self_inner):
                    return None

            return Handle()

    monkeypatch.setattr(agent_module.database, "create_escalation", fake_create_escalation)
    monkeypatch.setattr(agent_module.database, "save_caller", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        assistant,
        "_monitor_escalation_resolution",
        fake_monitor,
    )

    result = await assistant.create_escalation(
        SimpleNamespace(session=FakeSession()),
        "user-1",
        "Severe headache",
        "high",
        "en",
        next_step="wait",
    )

    assert "REQ-ABC123" in result
    assert not calls
    assert result == (
        "Successfully created escalation. The Reference ID is REQ-ABC123. "
        "Would you like me to play hold music while you wait?"
    )


def test_build_llm_uses_groq_then_gemini(monkeypatch) -> None:
    created = []

    class FakeLLM:
        def __init__(self, label):
            self.label = label

    class FakeGroq:
        @staticmethod
        def LLM(**kwargs):
            created.append(("groq", kwargs))
            return FakeLLM("groq")

    class FakeFallbackAdapter:
        def __init__(self, *, llm, **kwargs):
            created.append(("fallback", llm, kwargs))
            self.llm = llm
            self.kwargs = kwargs

    monkeypatch.setattr(agent_module, "groq", FakeGroq)
    monkeypatch.setattr(agent_module, "FallbackAdapter", FakeFallbackAdapter)
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")

    llm = agent_module._build_llm()

    assert isinstance(llm, FakeFallbackAdapter)
    assert created[0][0] == "groq"
    assert created[0][1]["max_completion_tokens"] == 120
    assert created[1][0] == "fallback"
    assert len(created[1][1]) == 2
    assert created[1][1][0].label == "groq"


def test_llm_defaults_are_safe() -> None:
    assert agent_module.GROQ_MODEL == "llama-3.1-8b-instant"
    assert agent_module.LLM_FALLBACK_ATTEMPT_TIMEOUT >= 10


def test_caller_memory_can_store_and_find_reference(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "caller_memory.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    database.init_db()

    assert database.save_caller(
        "user-123",
        "Priya Sharma",
        "en",
        {"age_band": "30-40", "escalation_ref": "REQ-123ABC"},
        escalation_reference="REQ-123ABC",
    )

    by_name = database.find_caller("Priya Sharma")
    by_ref = database.find_caller("REQ-123ABC")

    assert by_name is not None
    assert by_ref is not None
    assert by_name["user_id"] == "user-123"
    assert by_name["escalation_reference"] == "REQ-123ABC"
    assert by_ref["name"] == "Priya Sharma"
    assert by_ref["facts"]["escalation_ref"] == "REQ-123ABC"


@pytest.mark.asyncio
async def test_play_hold_music_passes_async_audio_stream(monkeypatch) -> None:
    assistant = Assistant()
    seen = {}

    class FakeHandle:
        async def wait_for_playout(self):
            return None

    class FakeSession:
        def say(self, text, *, audio=None, allow_interruptions=None, add_to_chat_ctx=None):
            seen["text"] = text
            seen["audio_is_async_iterable"] = hasattr(audio, "__aiter__")
            seen["allow_interruptions"] = allow_interruptions
            seen["add_to_chat_ctx"] = add_to_chat_ctx
            return FakeHandle()

    ctx = SimpleNamespace(session=FakeSession())

    result = await assistant.play_hold_music(ctx)

    assert result == "Hold music finished playing."
    assert seen["text"] == ""
    assert seen["audio_is_async_iterable"] is True
    assert seen["allow_interruptions"] is True
    assert seen["add_to_chat_ctx"] is False


@pytest.mark.asyncio
async def test_escalation_watcher_interrupts_and_speaks(monkeypatch) -> None:
    assistant = Assistant()
    polls = []
    sleeps = {"count": 0}

    class FakeSession:
        def __init__(self):
            self.interrupted = False
            self.spoken = []

        async def interrupt(self, force=False):
            self.interrupted = force

        def say(self, text, *, allow_interruptions=None):
            self.spoken.append((text, allow_interruptions))

            class Handle:
                async def wait_for_playout(self_inner):
                    return None

            return Handle()

    async def fake_sleep(_seconds):
        sleeps["count"] += 1
        return None

    def fake_status(reference_id):
        polls.append(reference_id)
        return {
            "status": "resolved",
            "human_response": "Please book a routine follow-up.",
        }

    monkeypatch.setattr(agent_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(agent_module.database, "get_escalation_status", fake_status)

    session = FakeSession()
    await assistant._monitor_escalation_resolution(session, "REQ-ABC123")

    assert polls == ["REQ-ABC123"]
    assert sleeps["count"] == 1
    assert session.interrupted is True
    assert session.spoken[0][0].startswith("A human specialist reviewed your request.")
    assert session.spoken[0][1] is False


@pytest.mark.asyncio
async def test_create_escalation_call_later_saves_name_and_reference(monkeypatch) -> None:
    assistant = Assistant()
    saved_calls = []

    def fake_create_escalation(user_id: str, summary: str, urgency: str, language: str):
        return "REQ-ZYX789"

    def fake_save_caller(
        user_id: str,
        name: str,
        language_preference: str,
        facts,
        escalation_reference=None,
    ):
        saved_calls.append(
            {
                "user_id": user_id,
                "name": name,
                "language_preference": language_preference,
                "facts": facts,
                "escalation_reference": escalation_reference,
            }
        )
        return True

    monkeypatch.setattr(agent_module.database, "create_escalation", fake_create_escalation)
    monkeypatch.setattr(agent_module.database, "save_caller", fake_save_caller)
    monkeypatch.setattr(assistant, "play_hold_music", lambda context: None)

    result = await assistant.create_escalation(
        SimpleNamespace(),
        "user-2",
        "Need a follow-up review",
        "medium",
        "hi",
        next_step="call_later",
        caller_name="Priya Sharma",
        caller_facts='{"age_band":"30-40"}',
    )

    assert "REQ-ZYX789" in result
    assert "Priya Sharma" in result
    assert saved_calls
    assert saved_calls[0]["name"] == "Priya Sharma"
    assert saved_calls[0]["language_preference"] == "hi"
    assert saved_calls[0]["facts"]["escalation_ref"] == "REQ-ZYX789"
    assert saved_calls[0]["escalation_reference"] == "REQ-ZYX789"
    assert saved_calls[0]["facts"]["age_band"] == "30-40"


@pytest.mark.asyncio
async def test_create_escalation_call_later_requires_name(monkeypatch) -> None:
    assistant = Assistant()

    def fake_create_escalation(user_id: str, summary: str, urgency: str, language: str):
        return "REQ-ZYX789"

    monkeypatch.setattr(agent_module.database, "create_escalation", fake_create_escalation)
    monkeypatch.setattr(agent_module.database, "save_caller", lambda *args, **kwargs: True)

    result = await assistant.create_escalation(
        SimpleNamespace(session=SimpleNamespace()),
        "user-2",
        "Need a follow-up review",
        "medium",
        "hi",
        next_step="call_later",
        caller_name="",
        caller_facts='{"age_band":"30-40"}',
    )

    assert "full name" in result.lower()
    assert "ask for their name first" in result.lower()
