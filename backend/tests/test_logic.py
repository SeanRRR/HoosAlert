import pytest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ml.logic import _ai_score, score_incident, _fallback_score

# Mock data for testing
MOCK_TEXT = "There is a fire in Building A"
MOCK_DATA = {
    "incident_type": "fire",
    "location": "Building A",
    "computingID": "abc123",
    "timestamp": "2026-03-21T12:00:00Z",
}

# --- TESTS FOR _ai_score ---

@patch("src.ml.logic._GEMINI_API_KEY", "test-key")
@patch("src.ml.logic.genai.Client")
def test_ai_score_success(mock_client_cls):
    """
    Test _ai_score when the Gemini API call succeeds.
    """
    # Mock the Gemini API response
    mock_response = MagicMock(
        text='{"severity": 5, "risk_label": "security", "confidence": 0.91, "reason_codes": ["keyword_weapon"]}'
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    # Call the function
    result = _ai_score(MOCK_TEXT)

    # Assertions
    assert result["severity"] == 5
    assert result["risk_label"] == "security"
    assert result["confidence"] == pytest.approx(0.91)
    assert result["reason_codes"] == ["keyword_weapon"]
    assert result["fallback_used"] is False
    mock_client.models.generate_content.assert_called_once()


@patch("src.ml.logic._GEMINI_API_KEY", "test-key")
@patch("src.ml.logic.genai.Client")
def test_ai_score_failure(mock_client_cls):
    """
    Test _ai_score when the Gemini API call fails.
    """
    # Mock the Gemini API to raise an exception
    mock_client_cls.side_effect = Exception("Gemini API error")

    # Call the function
    result = _ai_score(MOCK_TEXT)

    # Assertions
    assert result["severity"] == _fallback_score(MOCK_TEXT)["severity"]
    assert result["fallback_used"] is True


# --- TESTS FOR score_incident ---

@patch("src.ml.logic._GEMINI_API_KEY", "test-key")
@patch("src.ml.logic._ai_score")
def test_score_incident_with_ai(mock_ai_score):
    """
    Test score_incident when AI scoring works.
    """
    # Mock the _ai_score function
    mock_ai_score.return_value = {
        "severity": 5,
        "risk_label": "security",
        "confidence": 0.88,
        "reason_codes": ["keyword_weapon"],
        "model_version": "gemini-test",
        "prompt_version": "v2",
        "context_count": 0,
        "fallback_used": False,
        "scored_at": "2026-03-22T00:00:00+00:00",
    }

    # Call the function
    result = score_incident(MOCK_DATA)

    # Assertions
    assert result["incident"]["incident_type"] == "fire"
    assert result["score"]["severity"] == 5
    assert result["score"]["risk_label"] == "security"
    mock_ai_score.assert_called_once()


@patch("src.ml.logic._GEMINI_API_KEY", "test-key")
@patch("src.ml.logic._ai_score")
def test_score_incident_fallback(mock_ai_score):
    """
    Test score_incident when AI scoring returns the fallback score.
    """
    expected_text = (
        "Incident Type: fire, Description: , Location: Building A, "
        "Reporter: abc123, Timestamp: 2026-03-21T12:00:00Z"
    )
    mock_ai_score.return_value = _fallback_score(expected_text)

    # Call the function
    result = score_incident(MOCK_DATA)

    # Assertions
    fallback_result = _fallback_score(expected_text)
    assert result["score"]["severity"] == fallback_result["severity"]
    assert result["score"]["fallback_used"] is True
