import subprocess
import sys
from pathlib import Path
#validate the script in validate_restaurant.py
def test_restaurants_json_validates():
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "validate_restaurants.py"
    data = repo_root / "data" / "restaurants.json"

    result = subprocess.run(
        [sys.executable, str(script), str(data)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "Validation failed!\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )