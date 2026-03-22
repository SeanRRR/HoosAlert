import os
import sys
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ml.confidence import incident_match_confidence


INCIDENT_A = {
    "description": "Suspicious unattended bag near Old Cabell Hall",
    "location": "Old Cabell Hall",
    "latitude": 38.0313,
    "longitude": -78.5031,
    "timestamp": "2026-03-22T05:00:00Z",
    "severity": 4,
    "risk_label": "suspicious_activity",
}

INCIDENT_B = {
    "description": "Unattended backpack reported outside Old Cabell Hall",
    "location": "Old Cabell Hall",
    "latitude": 38.0314,
    "longitude": -78.5030,
    "timestamp": "2026-03-22T05:12:00Z",
    "severity": 4,
    "risk_label": "suspicious_activity",
}

LOW_INFORMATION_INCIDENT_1 = {
    "description": "Suspicious unattended bag near Old Cabell Hall",
}

LOW_INFORMATION_INCIDENT_2 = {
    "description": "Unattended bag near Old Cabell Hall",
}


def test_incident_match_confidence_deterministic_only():
    result = incident_match_confidence(INCIDENT_A, INCIDENT_B, use_gemini=False)

    assert result["confidence"] > 0.5
    assert result["deterministic_score"] > 0.5
    assert result["fallback_used"] is True
    assert "feature_distance" in result["reason_codes"] or "feature_text" in result["reason_codes"]
    assert 0.0 < result["confidence"] < 1.0


@patch("src.ml.confidence._gemini_api_key", return_value="test-key")
@patch("src.ml.confidence.genai.Client")
def test_incident_match_confidence_with_gemini(mock_client_cls, _mock_api_key):
    mock_response = MagicMock(
        text='{"semantic_similarity": 0.92, "match_confidence": 0.9, "reason_codes": ["semantic_description_match"]}'
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    result = incident_match_confidence(INCIDENT_A, INCIDENT_B, use_gemini=True)

    assert result["fallback_used"] is False
    assert result["semantic_similarity"] == 0.92
    assert result["confidence"] > 0.5
    assert "semantic_description_match" in result["reason_codes"]
    assert result["confidence"] < 1.0


def test_missing_information_applies_confidence_decay():
    result = incident_match_confidence(LOW_INFORMATION_INCIDENT_1, LOW_INFORMATION_INCIDENT_2, use_gemini=False)

    assert result["information_coverage"] < 1.0
    assert "information_decay_applied" in result["reason_codes"]
    assert result["confidence"] < 0.9
