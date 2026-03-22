import re


# maps messy text → your frontend keys
LOCATION_ALIASES = {
    "alderman library": "alderman-library",
    "clemons library": "clemons-library",
    "shannon library": "shannon-library",
    "newcomb hall": "newcomb-hall",
    "rotunda": "rotunda",
    "lawn": "lawn",
    "scott stadium": "scott-stadium",
    "uva hospital": "uva-medical-center",
    "student health": "student-health",
}


def normalize(text: str) -> str:
    return text.lower()


def detect_location(text: str):
    text = normalize(text)


    for phrase, key in LOCATION_ALIASES.items():
        if phrase in text:
            return key


    return None



