import uuid
from datetime import datetime
from typing import Dict, Any, Optional


def generate_event_id() -> str:
    return f"event_{uuid.uuid4().hex[:20]}"


def generate_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:16]}"


def generate_item_id() -> str:
    return f"item_{uuid.uuid4().hex[:20]}"


def create_event(event_type: str, **kwargs) -> Dict[str, Any]:
    event = {
        "event_id": generate_event_id(),
        "type": event_type,
    }
    event.update(kwargs)
    return event


def create_session_created_event(session_id: str, model: str, 
                                 input_audio_format: str = "pcm16",
                                 turn_detection: Optional[Dict] = None) -> Dict[str, Any]:
    session = {
        "id": session_id,
        "object": "realtime.session",
        "model": model,
        "modalities": ["text"],
        "input_audio_format": input_audio_format,
        "input_audio_transcription": None,
        "turn_detection": turn_detection or {
            "type": "server_vad",
            "threshold": 0.5,
            "silence_duration_ms": 200
        }
    }
    return create_event("session.created", session=session)


def create_session_updated_event(session_id: str, model: str,
                                 input_audio_format: str = "pcm16",
                                 turn_detection: Optional[Dict] = None) -> Dict[str, Any]:
    session = {
        "id": session_id,
        "object": "realtime.session",
        "model": model,
        "modalities": ["text"],
        "input_audio_format": input_audio_format,
        "input_audio_transcription": None,
        "turn_detection": turn_detection
    }
    return create_event("session.updated", session=session)


def create_error_event(error_type: str, code: str, message: str, 
                       param: Optional[str] = None, 
                       event_id: Optional[str] = None) -> Dict[str, Any]:
    error = {
        "type": error_type,
        "code": code,
        "message": message,
    }
    if param:
        error["param"] = param
    if event_id:
        error["event_id"] = event_id
    
    return create_event("error", error=error)


def create_speech_started_event(audio_start_ms: int, item_id: str) -> Dict[str, Any]:
    return create_event(
        "input_audio_buffer.speech_started",
        audio_start_ms=audio_start_ms,
        item_id=item_id
    )


def create_speech_stopped_event(audio_end_ms: int, item_id: str) -> Dict[str, Any]:
    return create_event(
        "input_audio_buffer.speech_stopped",
        audio_end_ms=audio_end_ms,
        item_id=item_id
    )


def create_input_audio_buffer_committed_event(previous_item_id: str, item_id: str) -> Dict[str, Any]:
    return create_event(
        "input_audio_buffer.committed",
        previous_item_id=previous_item_id,
        item_id=item_id
    )


def create_conversation_item_created_event(item_id: str, previous_item_id: str) -> Dict[str, Any]:
    return create_event(
        "conversation.item.created",
        previous_item_id=previous_item_id,
        item={
            "id": item_id,
            "object": "realtime.item",
            "type": "message",
            "status": "completed",
            "role": "user",
            "content": [{"type": "input_audio", "transcript": None}]
        }
    )


def create_transcription_text_event(item_id: str, content_index: int,
                                    language: str, emotion: str,
                                    text: str, stash: str) -> Dict[str, Any]:
    return create_event(
        "conversation.item.input_audio_transcription.text",
        item_id=item_id,
        content_index=content_index,
        language=language,
        emotion=emotion,
        text=text,
        stash=stash
    )


def create_transcription_completed_event(item_id: str, content_index: int,
                                         language: str, emotion: str,
                                         transcript: str) -> Dict[str, Any]:
    return create_event(
        "conversation.item.input_audio_transcription.completed",
        item_id=item_id,
        content_index=content_index,
        language=language,
        emotion=emotion,
        transcript=transcript
    )


def create_transcription_failed_event(item_id: str, content_index: int,
                                      code: str, message: str, param: str) -> Dict[str, Any]:
    return create_event(
        "conversation.item.input_audio_transcription.failed",
        item_id=item_id,
        content_index=content_index,
        error={
            "code": code,
            "message": message,
            "param": param
        }
    )


def create_session_finished_event() -> Dict[str, Any]:
    return create_event("session.finished")
