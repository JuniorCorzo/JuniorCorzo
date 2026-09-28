import os
import re
import unittest
import urllib.request
import urllib.error

README_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "README.md"))

class TestReadme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(README_PATH, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_portfolio_link_present(self):
        """Verify prominent portfolio link https://angelcorzo.dev is present."""
        self.assertIn("https://angelcorzo.dev", self.content, "Portfolio link https://angelcorzo.dev missing from README")

    def test_defunct_cyclic_app_absent(self):
        """Verify defunct cyclic.app is completely removed."""
        self.assertNotIn("cyclic.app", self.content, "Defunct domain cyclic.app found in README")

    def test_required_sections_present(self):
        """Verify Profile Header, About/Bio, Tech Stack, Featured Projects, GitHub Stats, Contact."""
        content_lower = self.content.lower()

        # Profile Header: Angel Corzo and Fullstack Developer
        self.assertTrue("angel corzo" in content_lower, "Header missing 'Angel Corzo'")
        self.assertTrue("fullstack" in content_lower, "Header missing 'Fullstack'")

        # About / Bio
        has_bio = any(k in content_lower for k in ["about", "bio", "overview", "introduction"]) or "colombia" in content_lower
        self.assertTrue(has_bio, "Missing About/Bio section")

        # Tech Stack
        has_tech_stack = any(k in content_lower for k in ["tech stack", "skills", "technologies"])
        self.assertTrue(has_tech_stack, "Missing Tech Stack section")

        # Featured Projects
        has_projects = any(k in content_lower for k in ["featured projects", "projects", "featured repositories"])
        self.assertTrue(has_projects, "Missing Featured Projects section")
        self.assertTrue("handly" in content_lower, "Missing project handly")
        self.assertTrue("nivo" in content_lower, "Missing project Nivo")
        self.assertTrue("secop-agent" in content_lower, "Missing project secop-agent")
        self.assertTrue("instrumentsmanage" in content_lower, "Missing project InstrumentsManage")

        # GitHub Stats
        has_stats = any(k in content_lower for k in ["github stats", "stats", "streak"])
        self.assertTrue(has_stats, "Missing GitHub Stats section")

        # Contact
        has_contact = any(k in content_lower for k in ["contact", "socials", "connect"])
        self.assertTrue(has_contact, "Missing Contact / Socials section")

    def test_http_links_validity(self):
        """Verify all extracted HTTP/HTTPS links respond with HTTP 200/30x (excluding rate limits/temporary pauses)."""
        urls = set(re.findall(r'https?://[^\s\)\]\"\'\`<>]+', self.content))
        self.assertGreater(len(urls), 0, "No URLs found in README")

        RATE_LIMITED_OR_BLOCKING_DOMAINS = {
            "linkedin.com",
            "github-readme-stats.vercel.app",
        }

        failed_urls = []
        for url in sorted(urls):
            is_edge_case = any(d in url for d in RATE_LIMITED_OR_BLOCKING_DOMAINS)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status not in (200, 201, 202, 204, 301, 302, 307, 308):
                        failed_urls.append((url, resp.status))
            except urllib.error.HTTPError as e:
                if is_edge_case and e.code in (403, 429, 503, 999):
                    continue
                failed_urls.append((url, f"HTTPError {e.code}"))
            except Exception as e:
                failed_urls.append((url, f"Exception: {type(e).__name__} {e}"))

        self.assertEqual(failed_urls, [], f"Found broken links: {failed_urls}")

if __name__ == "__main__":
    unittest.main()
