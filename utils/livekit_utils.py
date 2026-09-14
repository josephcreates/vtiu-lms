import os
import time
from livekit import api

def build_livekit_token(room_name: str, participant_identity: str, participant_name: str, is_publisher: bool = False):
    """
    Build a LiveKit Access Token.
    """
    api_key = os.environ.get('LIVEKIT_API_KEY')
    api_secret = os.environ.get('LIVEKIT_API_SECRET')
    
    if not api_key or not api_secret:
        raise RuntimeError("LiveKit API Key or Secret not configured.")
        
    token = api.AccessToken(api_key, api_secret) \
        .with_identity(participant_identity) \
        .with_name(participant_name) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=is_publisher,
            can_subscribe=True,
            can_publish_data=True
        ))
    
    return token.to_jwt()
