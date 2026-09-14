"""LiveKit access-token helpers."""


def build_livekit_token(api_key, api_secret, room_name, identity, display_name, role):
    """Build a short-lived token for a LiveKit room participant."""
    if not api_key or not api_secret:
        raise RuntimeError("LiveKit is not configured.")

    try:
        from livekit import api
    except ImportError as exc:
        raise RuntimeError("LiveKit token support is unavailable.") from exc

    can_publish = role == 'publisher'
    grants = api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=can_publish,
        can_subscribe=True,
    )
    return (
        api.AccessToken(api_key, api_secret)
        .with_identity(str(identity))
        .with_name(display_name or str(identity))
        .with_grants(grants)
        .to_jwt()
    )