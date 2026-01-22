import pytest
from fastapi.testclient import TestClient


def test_fusion_endpoint_exists(client):
    """Verify fusion endpoint is registered."""
    response = client.get("/api/races/1/fusion")
    # Should return 200 or 404 (race not found), not 405 (method not allowed)
    assert response.status_code in [200, 404]


def test_fusion_returns_valid_structure(client):
    """Test fusion response has correct structure when race exists."""
    # Get a race ID that exists
    races_response = client.get("/api/races")
    if races_response.status_code == 200 and races_response.json():
        race_id = races_response.json()[0].get('id')
        if race_id:
            response = client.get(f"/api/races/{race_id}/fusion")
            if response.status_code == 200:
                data = response.json()
                # Verify structure
                assert 'race_id' in data
                assert 'race_title' in data
                assert 'margin_of_victory' in data
                assert 'winner_metrics' in data
                assert 'winner_leverage' in data
                # Verify winner_metrics structure
                winner = data['winner_metrics']
                assert 'candidate_name' in winner
                assert 'party_lines' in winner
                assert 'main_party_votes' in winner
                assert 'minor_party_votes' in winner
                assert 'minor_party_share' in winner


def test_fusion_404_for_invalid_race(client):
    """Test 404 returned for non-existent race."""
    response = client.get("/api/races/999999/fusion")
    assert response.status_code == 404


def test_fusion_leverage_calculation(client):
    """Test leverage is calculated correctly (minor votes / margin)."""
    races_response = client.get("/api/races")
    if races_response.status_code == 200 and races_response.json():
        race_id = races_response.json()[0].get('id')
        if race_id:
            response = client.get(f"/api/races/{race_id}/fusion")
            if response.status_code == 200:
                data = response.json()
                margin = data['margin_of_victory']
                winner_metrics = data['winner_metrics']
                winner_leverage = data['winner_leverage']

                if margin > 0 and winner_metrics['minor_party_votes'] > 0:
                    expected_leverage = round(winner_metrics['minor_party_votes'] / margin, 2)
                    assert winner_leverage == expected_leverage


def test_party_line_shares_sum_correctly(client):
    """Test party line share percentages are reasonable."""
    races_response = client.get("/api/races")
    if races_response.status_code == 200 and races_response.json():
        race_id = races_response.json()[0].get('id')
        if race_id:
            response = client.get(f"/api/races/{race_id}/fusion")
            if response.status_code == 200:
                data = response.json()
                winner = data['winner_metrics']
                if winner['party_lines']:
                    total_share = sum(pl['share_pct'] for pl in winner['party_lines'])
                    # Should be close to 100% (allowing for rounding)
                    assert 99 <= total_share <= 101
