import inspect
import json
import os
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

# Ensure root directory is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.fetch_contributions import (
    USERNAME_REGEX,
    validate_username,
    get_target_user,
    build_data,
    save_contributions,
)
from scripts.render_stats_svg import (
    render_stats,
    short_date,
    span_date,
)
from scripts.generate_streak_svg import (
    get_streak_data,
    render_streak_svg,
)
from scripts.render_heatmap_svg import (
    render_heatmap,
)
from scripts.make_ascii_svg import (
    render_ascii_svg,
)
from scripts.prep_photo import (
    crop_subject_bounds,
)


class TestAuditScripts(unittest.TestCase):

    def test_username_validation(self):
        """Verify username regex validation in fetch_contributions.py."""
        # Valid GitHub usernames
        valid_users = ["JuniorCorzo", "octocat", "torvalds", "user-123", "a", "a-b-c"]
        for u in valid_users:
            self.assertEqual(validate_username(u), u, f"Failed for valid user {u}")

        # Malicious and invalid injection characters
        invalid_users = [
            "Junior;rm -rf",
            "../../etc/passwd",
            "user/repo",
            "-starts-with-dash",
            "ends-with-dash-",
            "user..name",
            "invalid@char",
            "user space",
            "",
            "a" * 40,  # exceeds max 39 chars
            "double--dash", # GitHub doesn't allow consecutive hyphens
        ]
        for u in invalid_users:
            with self.assertRaises(ValueError, msg=f"Should reject invalid username {u}"):
                validate_username(u)

    def test_zero_division_and_empty_dataset(self):
        """Verify zero-division and empty dataset handling in render_stats_svg.py and fetch_contributions.py."""
        empty_data = {
            "username": "JuniorCorzo",
            "generated_at": "2026-10-21T00:00:00Z",
            "range": {"start": None, "end": None},
            "total_contributions": 0,
            "active_days": 0,
            "avg_per_active_day": 0,
            "current_streak": {"length": 0, "start": None, "end": None},
            "longest_streak": {"length": 0, "start": None, "end": None},
            "best_day": {"date": None, "count": 0},
            "monthly": [],
            "days": [],
        }

        # Must not raise ZeroDivisionError and must produce valid SVG
        svg = render_stats(empty_data)
        self.assertIn("<svg", svg)
        self.assertIn("/ 0", svg)
        self.assertIn("0% of the year", svg)
        self.assertIn("JuniorCorzo@github: ~$ ./stats.sh", svg)

        # Verify build_data with empty days list
        built = build_data([], username="JuniorCorzo")
        self.assertEqual(built["total_contributions"], 0)
        self.assertEqual(built["active_days"], 0)
        self.assertEqual(built["avg_per_active_day"], 0)
        self.assertEqual(built["best_day"], {"date": None, "count": 0})

    def test_safe_data_ingestion_no_third_party(self):
        """Verify safe data ingestion without reaching out to insecure third-party endpoints."""
        streak_script_path = os.path.join(ROOT_DIR, "scripts", "generate_streak_svg.py")
        with open(streak_script_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Insecure endpoint jogruber.de must be completely stripped
        self.assertNotIn("jogruber.de", content, "Insecure third-party endpoint jogruber.de found")

        # Mock urllib to ensure no external network call is made during get_streak_data
        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = AssertionError("Network call attempted!")
            data = get_streak_data(user="JuniorCorzo", data_file="/nonexistent/path/data.json")
            self.assertIn("contributions", data)
            self.assertIn("total", data)

    def test_utf8_encoding_in_file_writes(self):
        """Verify UTF-8 encoding in all file operations across scripts."""
        scripts_to_check = [
            "fetch_contributions.py",
            "generate_streak_svg.py",
            "render_stats_svg.py",
            "render_heatmap_svg.py",
            "make_ascii_svg.py",
        ]
        for script_name in scripts_to_check:
            path = os.path.join(ROOT_DIR, "scripts", script_name)
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()

            # Ensure open() calls with mode 'w' specify encoding="utf-8"
            for match in re.finditer(r'open\([^)]+\)', code):
                call = match.group(0)
                if '"w"' in call or "'w'" in call:
                    self.assertIn(
                        'encoding="utf-8"',
                        call,
                        f"Missing encoding='utf-8' in open() call in {script_name}: {call}",
                    )

    def test_dynamic_user_configuration(self):
        """Verify dynamic user configuration via args, env vars, and default."""
        # 1. Default to JuniorCorzo
        with patch.dict(os.environ, {}, clear=True):
            user = get_target_user(args=[])
            self.assertEqual(user, "JuniorCorzo")

        # 2. Env variable GH_PROFILE_USER
        with patch.dict(os.environ, {"GH_PROFILE_USER": "EnvUser"}):
            user = get_target_user(args=[])
            self.assertEqual(user, "EnvUser")

        # 3. CLI argument precedence over env
        with patch.dict(os.environ, {"GH_PROFILE_USER": "EnvUser"}):
            user = get_target_user(args=["script_name", "CliUser"])
            self.assertEqual(user, "CliUser")

    def test_prep_photo_defensive_bounds(self):
        """Verify defensive bounds check in prep_photo on empty or zero-alpha inputs."""
        import numpy as np

        # Empty alpha (all zeros)
        alpha_zeros = np.zeros((100, 100), dtype=np.uint8)
        out_mock = np.full((100, 100), 128, dtype=np.uint8)
        
        # Must not raise ValueError: zero-size array
        canvas = crop_subject_bounds(alpha_zeros, out_mock)
        self.assertIsNotNone(canvas)
        self.assertEqual(canvas.shape, (100, 100))


if __name__ == "__main__":
    unittest.main()
