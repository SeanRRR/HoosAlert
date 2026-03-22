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

@patch("src.ml.logic.genai.GenerativeModel", create=True)
def test_ai_score_success(mock_model):
    """
    Test _ai_score when the Gemini API call succeeds.
    """
    # Mock the Gemini API response
    mock_instance = MagicMock()
    mock_instance.generate_content.return_value = MagicMock(
        text='{"severity": 5, "type": "high_risk"}'
    )
    mock_model.return_value = mock_instance

    # Call the function
    result = _ai_score(MOCK_TEXT)

    # Assertions
    assert result == {"severity": 5, "type": "high_risk"}
    mock_instance.generate_content.assert_called_once()


@patch("src.ml.logic.genai.GenerativeModel", create=True)
def test_ai_score_failure(mock_model):
    """
    Test _ai_score when the Gemini API call fails.
    """
    # Mock the Gemini API to raise an exception
    mock_model.side_effect = Exception("Gemini API error")

    # Call the function
    result = _ai_score(MOCK_TEXT)

    # Assertions
    assert result == _fallback_score(MOCK_TEXT)  # Should fall back to the fallback score


# --- TESTS FOR score_incident ---

@patch("src.ml.logic._GEMINI_API_KEY", "test-key")
@patch("src.ml.logic._ai_score")
def test_score_incident_with_ai(mock_ai_score):
    """
    Test score_incident when AI scoring works.
    """
    # Mock the _ai_score function
    mock_ai_score.return_value = {"severity": 5, "type": "high_risk"}

    # Call the function
    result = score_incident(MOCK_DATA)

    # Assertions
    assert result["severity"] == 5
    assert result["type"] == "high_risk"
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
    assert result == fallback_result
