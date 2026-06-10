from v2ray_auto.core.state import RealityProfileState


def test_reality_profile_state_shape():
    state = RealityProfileState(
        private_key="private",
        public_key="public",
        client_id="00000000-0000-0000-0000-000000000000",
        short_id="abc123",
    )

    assert state.private_key == "private"
    assert state.public_key == "public"
    assert state.client_id == "00000000-0000-0000-0000-000000000000"
    assert state.short_id == "abc123"
