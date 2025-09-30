import math
from datetime import datetime, timedelta
from typing import List, Dict, Any
from hashlib import md5
from config import logger
from models.db_utils import db
from models.recording_session import RecordingSession
from models.recording_segment import RecordingChunk
from models.recording_session_tip import RecordingSessionTip
from models.user import User
from fcm_utils import send_push_to_users
from openai_utils import get_reply_json

# Simple rate limiting constants
MIN_SECONDS_BETWEEN_TIPS = 45
MAX_TIPS_PER_SESSION = 8


def _aggregate_transcript_with_timestamps(session_id: str) -> List[Dict[str, Any]]:
    """Return list of {'ts': seconds_from_start, 'text': '...'} for each chunk's transcript.
    Estimate timestamps from PCM data length if available; fallback to index * 55s.
    """
    chunks = RecordingChunk.list_by_session(session_id)
    results = []
    for ch in chunks:
        if not ch.transcription_text:
            continue
        # Estimate duration from raw size (after WAV header) if WAV-like
        est_duration = None
        try:
            data = bytes(ch.data) if ch.data else b''
            if len(data) > 44 and data[0:4] == b'RIFF' and data[8:12] == b'WAVE':
                import struct
                # data chunk size at last 4 bytes of header if classic 44-byte header, else search
                idx = data.find(b'data')
                if idx != -1 and idx + 8 <= len(data):
                    data_size = struct.unpack('<I', data[idx+4:idx+8])[0]
                    # 16000 samples/sec * 2 bytes
                    est_duration = data_size / (16000 * 2)
        except Exception:
            pass
        if est_duration is None:
            est_duration = 55.0  # coarse fallback
        # Start time approximated by prior durations
        prior_seconds = 0.0
        for r in results:
            prior_seconds = max(prior_seconds, r['ts'])
        # Each chunk considered sequential; ts is total of previous durations
        total_duration_so_far = sum(r.get('duration', 0) for r in results)
        results.append({'ts': int(round(total_duration_so_far)), 'text': ch.transcription_text, 'duration': est_duration})
    return results


def _build_prompt(session: RecordingSession, transcript_segments: List[Dict[str, Any]], prior_tips: List[RecordingSessionTip]):
    objective = session.objective or 'Conversation practice'
    instructions = session.ai_instructions or 'Provide concise, constructive coaching suggestions to improve communication.'
    prior_formatted = '\n'.join([f"- {t.content}" for t in prior_tips]) or 'None yet.'
    transcript_str_lines = []
    for seg in transcript_segments[-6:]:  # last few segments for focus
        mm = seg['ts'] // 60
        ss = seg['ts'] % 60
        transcript_str_lines.append(f"[{mm:02d}:{ss:02d}] {seg['text']}")
    transcript_portion = '\n'.join(transcript_str_lines)
    system_content = f"""
You are ConversationCoach, an AI that provides real-time, highly actionable communication coaching tips.
Goal / Objective: {objective}
Custom Instructions: {instructions}
Previous Tips Already Sent (avoid duplicates or rephrasing):\n{prior_formatted}
Recent Transcript Portion (with timestamps):\n{transcript_portion}

Instructions:
- Return ONLY JSON matching this schema: {{"tips": [{{"text": "string"}}]}}
- Provide at most 2 new tips per invocation.
- Tips must be novel, specific, and less than 160 characters.
- If no new, valuable, non-redundant tip is warranted, return {{"tips": []}}.
""".strip()
    return system_content


def _call_model(user: User, system_content: str) -> List[str]:
    try:
        resp = get_reply_json(user, system_content, user_msg='')
        tips = resp.get('tips') or []
        out = []
        for t in tips:
            if isinstance(t, dict):
                txt = t.get('text')
                if txt and isinstance(txt, str):
                    out.append(txt.strip())
            elif isinstance(t, str):
                out.append(t.strip())
        return [t for t in out if t]
    except Exception as e:
        logger.error(f"AI tip generation failed: {e}")
        return []


def maybe_generate_and_push_tips(session_id: str):
    session = RecordingSession.query.get(session_id)
    if not session:
        return
    user = User.query.get(session.user_id)
    if not user:
        return
    # Load prior tips
    prior_tips = RecordingSessionTip.query.filter_by(session_id=session_id).order_by(RecordingSessionTip.created_on.asc()).all()
    if len(prior_tips) >= MAX_TIPS_PER_SESSION:
        return
    # Rate limit by last tip time
    from sqlalchemy import desc
    last_tip = RecordingSessionTip.query.filter_by(session_id=session_id).order_by(desc(RecordingSessionTip.created_on)).first()
    if last_tip and (datetime.utcnow() - (last_tip.created_on or datetime.utcnow())) < timedelta(seconds=MIN_SECONDS_BETWEEN_TIPS):
        return
    transcript_segments = _aggregate_transcript_with_timestamps(session_id)
    if not transcript_segments:
        return
    # Require some minimum transcript length growth
    total_chars = sum(len(seg['text']) for seg in transcript_segments)
    if total_chars < 150:  # wait for some content
        return
    system_prompt = _build_prompt(session, transcript_segments, prior_tips)
    new_tips = _call_model(user, system_prompt)
    if not new_tips:
        return
    created: List[RecordingSessionTip] = []
    for tip_text in new_tips:
        h = md5(tip_text.encode('utf-8')).hexdigest()
        exists = RecordingSessionTip.query.filter_by(session_id=session_id, content_hash=h).first()
        if exists:
            continue
        # Approx offset is end of current transcript (last segment ts + its duration)
        if transcript_segments:
            last_seg = transcript_segments[-1]
            offset_seconds = int(last_seg['ts'] + last_seg.get('duration', 0))
        else:
            offset_seconds = 0
        rec = RecordingSessionTip.create(session_id=session_id, user_id=session.user_id, content=tip_text, transcript_offset_seconds=offset_seconds, content_hash=h)
        created.append(rec)
        if len(prior_tips) + len(created) >= MAX_TIPS_PER_SESSION:
            break
    if not created:
        return
    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed committing tips: {e}")
        db.session.rollback()
        return
    # Push
    try:
        for tip in created:
            payload = {
                'type': 'coaching_tips',
                'session_id': session_id,
                'count': len(created),
                'tips_json': '\n'.join([c.content for c in created]),
                'title': 'New Tip',
                'body': tip.content
            }
            send_push_to_users([session.user_id], payload)
    except Exception as e:
        logger.error(f"Failed sending tip push: {e}")
