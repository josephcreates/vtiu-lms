import os
from utils.livekit import build_livekit_token as _build_livekit_token


def build_livekit_token(room_name: str, participant_identity: str, participant_name: str, is_publisher: bool = False):
    """Compatibility wrapper for older mobile callers.

    Delegates to the canonical helper so all token endpoints stay aligned on
    the same LiveKit room name, participant identity, display name, and role
    semantics.
    """
    api_key = os.environ.get('LIVEKIT_API_KEY')
    api_secret = os.environ.get('LIVEKIT_API_SECRET')
    return _build_livekit_token(
        api_key,
        api_secret,
        room_name,
        participant_identity,
        participant_name,
        'publisher' if is_publisher else 'audience',
    )
