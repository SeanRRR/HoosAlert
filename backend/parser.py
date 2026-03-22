from location_resolver import detect_location


def detect_severity(text: str) -> int:
    text = text.lower()


    if any(w in text for w in ["active threat", "gun", "shooting", "evacuate"]):
        return 5
    if "shelter" in text or "police responding" in text:
        return 4
    if "suspicious" in text:
        return 2
    return 3




def parse_alert(text: str):
    location_key = detect_location(text)
    severity = detect_severity(text)


    return {
        "title": "UVA Alert",
        "location_key": location_key,  # IMPORTANT (not coords yet)
        "severity": severity,
        "risk_label": (
            "critical" if severity == 5 else
            "high" if severity == 4 else
            "medium"
        ),
        "raw_text": text
    }
