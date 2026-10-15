import runpy
from pathlib import Path
import tempfile
import unittest

validate = runpy.run_path(str(Path(__file__).resolve().parents[1] / "verify-website.py"))["validate"]


class WebsiteVerificationTests(unittest.TestCase):
    def check(self, html, *, css=""):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / "index.html").write_text(html)
            (site / "styles.css").write_text(css)
            return validate(site)

    def test_existing_files_and_fragments_pass(self):
        self.assertEqual(self.check('<a href="/#iphone">iPhone</a><section id="iphone"></section>'
                                    '<link href="/styles.css?v=launch">'), [])

    def test_missing_assets_fail(self):
        self.assertIn("missing local target", self.check('<img src="/missing.svg">')[0])

    def test_missing_fragment_fails(self):
        self.assertIn("missing fragment", self.check('<a href="#missing">Link</a>')[0])

    def test_css_fonts_are_checked(self):
        self.assertIn("missing local target", self.check("", css='src: url("/missing.ttf")')[0])

    def test_external_links_do_not_need_network(self):
        self.assertEqual(self.check('<a href="https://apps.apple.com/us/app/id6820103568">App</a>'), [])

    def test_links_cannot_escape_the_site(self):
        self.assertIn("link leaves website", self.check('<a href="/../outside">Link</a>')[0])


if __name__ == "__main__":
    unittest.main()
