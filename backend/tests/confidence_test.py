import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ml.confidence import incident_match_confidence


HIGH_MATCH_INCIDENT_1 = {
    "description": "Suspicious unattended bag near Old Cabell Hall",
    "location": "Old Cabell Hall",
    "latitude": 38.0313,
    "longitude": -78.5031,
    "timestamp": "2026-03-22T05:00:00Z",
    "severity": 4,
    "risk_label": "suspicious_activity",
}

HIGH_MATCH_INCIDENT_2 = {
    "description": "Unattended backpack reported outside Old Cabell Hall",
    "location": "Old Cabell Hall",
    "latitude": 38.0314,
    "longitude": -78.5030,
    "timestamp": "2026-03-22T05:12:00Z",
    "severity": 4,
    "risk_label": "suspicious_activity",
}

MEDIUM_MATCH_INCIDENT_1 = {
    "description": "Student reports suspicious person near Newcomb Hall",
    "location": "Newcomb Hall",
    "latitude": 38.0340,
    "longitude": -78.5060,
    "timestamp": "2026-03-22T07:00:00Z",
    "severity": 3,
    "risk_label": "security",
}

MEDIUM_MATCH_INCIDENT_2 = {
    "description": "Possible trespassing complaint near the bookstore",
    "location": "University Bookstore",
    "latitude": 38.0351,
    "longitude": -78.5072,
    "timestamp": "2026-03-22T09:10:00Z",
    "severity": 3,
    "risk_label": "security",
}

LOW_MATCH_INCIDENT_1 = {
    "description": "Minor vehicle collision on Emmet Street with no injuries",
    "location": "Emmet St & University Ave",
    "latitude": 38.0305,
    "longitude": -78.5053,
    "timestamp": "2026-03-22T08:00:00Z",
    "severity": 2,
    "risk_label": "traffic",
}

LOW_MATCH_INCIDENT_2 = {
    "description": "Medical emergency reported at the Rotunda",
    "location": "Rotunda",
    "latitude": 38.0334,
    "longitude": -78.5032,
    "timestamp": "2026-03-22T16:30:00Z",
    "severity": 5,
    "risk_label": "medical",
}


def test_high_match_case_has_high_confidence():
    result = incident_match_confidence(HIGH_MATCH_INCIDENT_1, HIGH_MATCH_INCIDENT_2, use_gemini=False)

    assert result["confidence"] >= 0.7
    assert result["components"]["text"] > 0.2
    assert result["components"]["distance"] > 0.9
    assert result["components"]["time"] > 0.9


def test_medium_match_case_has_middle_confidence():
    result = incident_match_confidence(MEDIUM_MATCH_INCIDENT_1, MEDIUM_MATCH_INCIDENT_2, use_gemini=False)

    assert 0.35 <= result["confidence"] <= 0.8
    assert result["components"]["risk_label"] == 1.0
    assert result["components"]["distance"] is not None


def test_low_match_case_has_low_confidence():
    result = incident_match_confidence(LOW_MATCH_INCIDENT_1, LOW_MATCH_INCIDENT_2, use_gemini=False)

    assert result["confidence"] <= 0.45
    assert result["components"]["risk_label"] == 0.0
    assert result["components"]["severity"] < 0.5
