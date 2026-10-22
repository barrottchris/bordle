"""Flask route integration tests.

All Postgres / game-logic DB calls are mocked so these tests exercise only
route-level behaviour: session handling, redirects, status codes, and JSON
response shapes.
"""

from unittest.mock import patch, MagicMock

import pytest

from tests.helpers import (
    TEST_PLAYER_UID,
    TEST_COUNTRY,
    TEST_BORDERS,
    TEST_GAME_NUMBER,
    make_response_state,
)


# ── shared helpers ─────────────────────────────────────────────────────────────

def _seed_session(client, **extra):
    """Write test values into the Flask session before a request."""
    with client.session_transaction() as sess:
        sess["player_uid"] = TEST_PLAYER_UID
        sess["country_name"] = TEST_COUNTRY
        sess["game_number"] = TEST_GAME_NUMBER
        sess["game_date"] = "2026-03-22"
        sess["hard_mode"] = False
        sess.update(extra)


@pytest.fixture
def mock_build(app):
    """Patch everything _build_game_response() calls so templates can render."""
    with (
        patch("app.get_game_state", return_value=make_response_state()),
        patch("app.get_games_today_stats", return_value=(10, 75)),
        patch("app.get_total_games_count", return_value=100),
        patch("app.analytics", return_value={}),
        patch("app.iso_map", {}),
    ):
        yield


# ── /set_mode_and_play ─────────────────────────────────────────────────────────

class TestSetModeAndPlay:
    def test_hard_mode_stored_in_session_when_flag_sent(self, client):
        with patch("app.get_or_create_player_uid", return_value=(TEST_PLAYER_UID, False)):
            client.post(
                "/set_mode_and_play",
                data={"hard_mode": "on"},
                headers={"Cookie": f"player_uid={TEST_PLAYER_UID}"},
            )
        with client.session_transaction() as sess:
            assert sess.get("hard_mode") is True

    def test_easy_mode_stored_when_flag_absent(self, client):
        with patch("app.get_or_create_player_uid", return_value=(TEST_PLAYER_UID, False)):
            client.post(
                "/set_mode_and_play",
                data={},
                headers={"Cookie": f"player_uid={TEST_PLAYER_UID}"},
            )
        with client.session_transaction() as sess:
            assert sess.get("hard_mode") is False

    def test_redirects_to_game(self, client):
        with patch("app.get_or_create_player_uid", return_value=(TEST_PLAYER_UID, False)):
            resp = client.post(
                "/set_mode_and_play",
                data={"hard_mode": "on"},
                headers={"Cookie": f"player_uid={TEST_PLAYER_UID}"},
            )
        assert resp.status_code == 302
        assert "/game" in resp.headers["Location"]


# ── /game ──────────────────────────────────────────────────────────────────────

class TestGameRoute:
    def test_get_returns_200(self, client, mock_build):
        _seed_session(client)
        with patch("app.get_or_create_player_uid", return_value=(TEST_PLAYER_UID, False)):
            resp = client.get(
                "/game",
                headers={"Cookie": f"player_uid={TEST_PLAYER_UID}"},
            )
        assert resp.status_code == 200

    def test_post_guess_returns_200(self, client, mock_build):
        _seed_session(client)
        with (
            patch("app.get_or_create_player_uid", return_value=(TEST_PLAYER_UID, False)),
            patch("app.process_guess"),
        ):
            resp = client.post(
                "/game",
                data={"guess": TEST_BORDERS[0]},
                headers={"Cookie": f"player_uid={TEST_PLAYER_UID}"},
            )
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        ("state_overrides", "map_id"),
        [
            ({"attempts_left": 0}, "failureMap"),
            ({"correct_count": len(TEST_BORDERS)}, "victoryMap"),
        ],
    )
    def test_end_game_maps_use_local_basemap(self, client, app, state_overrides, map_id):
        _seed_session(client)
        with (
            patch("app.get_game_state", return_value=make_response_state(**state_overrides)),
            patch("app.get_games_today_stats", return_value=(10, 75)),
            patch("app.get_total_games_count", return_value=100),
            patch("app.analytics", return_value={}),
            patch("app.iso_map", {}),
            patch("app.get_or_create_player_uid", return_value=(TEST_PLAYER_UID, False)),
        ):
            response = client.get(
                "/game",
                headers={"Cookie": f"player_uid={TEST_PLAYER_UID}"},
            )

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert f'id="{map_id}"' in html
        assert "/static/map_data/world_terrain.jpg" in html
        assert "/static/map_data/world_labels.geojson" in html
        assert "api.maptiler.com" not in html

    def test_local_basemap_assets_are_served(self, client):
        terrain = client.get("/static/map_data/world_terrain.jpg")
        labels = client.get("/static/map_data/world_labels.geojson")

        assert terrain.status_code == 200
        assert terrain.mimetype == "image/jpeg"
        assert labels.status_code == 200
        label_data = labels.get_json()
        assert label_data["type"] == "FeatureCollection"
        assert label_data["features"]
        assert {feature["properties"]["kind"] for feature in label_data["features"]} == {"country"}


# ── /submit ────────────────────────────────────────────────────────────────────

class TestSubmitRoute:
    def test_correct_guess_returns_200(self, client, mock_build):
        _seed_session(client)
        with (
            patch("app.get_or_create_player_uid", return_value=(TEST_PLAYER_UID, False)),
            patch("app.process_guess"),
        ):
            resp = client.post(
                "/submit",
                data={"guess": TEST_BORDERS[0]},
                headers={"Cookie": f"player_uid={TEST_PLAYER_UID}"},
            )
        assert resp.status_code == 200

    def test_empty_guess_redirects_to_game(self, client):
        _seed_session(client)
        with patch("app.get_or_create_player_uid", return_value=(TEST_PLAYER_UID, False)):
            resp = client.post(
                "/submit",
                data={"guess": ""},
                headers={"Cookie": f"player_uid={TEST_PLAYER_UID}"},
            )
        assert resp.status_code == 302
        assert "/game" in resp.headers["Location"]

    def test_process_guess_is_called_with_the_submitted_guess(self, client, mock_build):
        _seed_session(client)
        with (
            patch("app.get_or_create_player_uid", return_value=(TEST_PLAYER_UID, False)),
            patch("app.process_guess") as mock_pg,
        ):
            client.post(
                "/submit",
                data={"guess": TEST_BORDERS[0]},
                headers={"Cookie": f"player_uid={TEST_PLAYER_UID}"},
            )
        assert mock_pg.call_args.args[0] == TEST_BORDERS[0]


# ── /api/player_stats ──────────────────────────────────────────────────────────

class TestApiPlayerStats:
    _MOCK_STATS = {
        "games_played": 10,
        "games_won": 7,
        "current_streak": 3,
        "best_streak": 5,
        "player_country": "UK",
        "player_city": "London",
        "last_updated": "2026-03-22",
        "migrated": False,
    }

    def test_returns_200_and_stats_for_known_player(self, client):
        with patch("app.get_player_stats", return_value=self._MOCK_STATS):
            resp = client.get(f"/api/player_stats?player_uid={TEST_PLAYER_UID}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "found"
        assert data["games_played"] == 10
        assert data["current_streak"] == 3
        assert data["success_rate"] == 70

    def test_returns_404_when_player_not_found(self, client):
        with patch("app.get_player_stats", return_value=None):
            resp = client.get(
                "/api/player_stats",
                headers={"Cookie": f"player_uid={TEST_PLAYER_UID}"},
            )
        assert resp.status_code == 404

    def test_returns_404_when_no_uid(self, client):
        """No cookie and no query param → 404, not 500."""
        with patch("app.get_player_stats", return_value=None):
            resp = client.get("/api/player_stats")
        assert resp.status_code == 404


# ── /leaderboard_data ─────────────────────────────────────────────────────────

class TestLeaderboardDataRoute:
    def test_passes_limit_parameter_to_backend(self, client):
        with patch("app.get_leaderboard_data", return_value={"daily": [], "all_time": []}) as mock_get:
            resp = client.get("/leaderboard_data?limit=all")
        assert resp.status_code == 200
        assert mock_get.call_count == 1
        assert mock_get.call_args.args[0] == 300

    def test_passes_numeric_limit_to_backend(self, client):
        with patch("app.get_leaderboard_data", return_value={"daily": [], "all_time": []}) as mock_get:
            resp = client.get("/leaderboard_data?limit=7")
        assert resp.status_code == 200
        assert mock_get.call_count == 1
        assert mock_get.call_args.args[0] == 7


# ── /reset ─────────────────────────────────────────────────────────────────────

class TestReset:
    def test_clears_session_and_redirects(self, client):
        _seed_session(client)
        resp = client.get("/reset")
        assert resp.status_code == 302
        with client.session_transaction() as sess:
            assert "country_name" not in sess
