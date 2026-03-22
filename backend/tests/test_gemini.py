import os
import sys
from pathlib import Path

from dotenv import load_dotenv


TESTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TESTS_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env", override=True)

os.environ["DEBUG_AI_SCORING"] = "1"

from src.ml.logic import _ai_score, _fallback_score


def main() -> int:
    text = " ".join(sys.argv[1:]).strip() or "There is a person in Building A"
    result = _ai_score(text)
    fallback = _fallback_score(text)

    print(f"Input: {text}")
    print(f"Result: {result}")

    if result == fallback:
        print("Status: fallback path used")
    else:
        print("Status: Gemini returned a non-fallback result")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
