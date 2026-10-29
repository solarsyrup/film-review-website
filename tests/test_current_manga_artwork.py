"""Local, network-free manga artwork matching regression tests.

Run: python -m unittest discover -s tests -p 'test_*.py'
Requires PyYAML.
"""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "current_artwork", Path(__file__).resolve().parents[1] / "scripts/import_current_artwork.py"
)
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)


class MangaArtworkTests(unittest.TestCase):
    def test_explicit_and_implicit_volume_parsing(self):
        self.assertEqual(art.split_book_title_and_volume("JoJolion - Hirohiko Araki"), ("JoJolion - Hirohiko Araki", None, False))
        self.assertEqual(art.split_book_title_and_volume("JoJolion Vol. 7"), ("JoJolion", 7, True))
        self.assertEqual(art.split_book_title_and_volume("JoJolion Volume 13"), ("JoJolion", 13, True))
        self.assertEqual(art.split_book_title_and_volume("JoJolion #3"), ("JoJolion", 3, True))
        self.assertEqual(art.split_book_title_and_volume("JoJolion", 6), ("JoJolion", 6, True))

    def test_volume_matching_must_be_exact(self):
        self.assertTrue(art.reading_matches_title("JoJolion, Vol. 3", "JoJolion", 3))
        self.assertTrue(art.reading_matches_title("JoJolion 3", "JoJolion", 3))
        self.assertFalse(art.reading_matches_title("JoJolion Vol. 1", "JoJolion", 3))
        self.assertFalse(art.reading_matches_title("JoJolion", "JoJolion", 3))
        self.assertTrue(art.reading_matches_title("JoJolion", "JoJolion", None))

    @patch.object(art, "get_json")
    def test_volume_3_chooses_3_not_1(self, fetch):
        fetch.return_value = {"docs": [
            {"title": "JoJolion Vol. 1", "author_name": ["Hirohiko Araki"], "cover_i": 11},
            {"title": "JoJolion, Vol. 3", "author_name": ["Araki, Hirohiko"], "cover_i": 33},
        ]}
        url = art.reading_art({"currentlyReading": "JoJolion", "currentlyReadingAuthor": "Hirohiko Araki", "currentlyReadingVolume": 3})
        self.assertEqual(url, "https://covers.openlibrary.org/b/id/33-L.jpg")

    @patch.object(art, "get_json")
    def test_missing_specific_volume_wont_use_series_art(self, fetch):
        fetch.return_value = {"docs": [{"title": "JoJolion Vol. 1", "cover_i": 11}]}
        self.assertIsNone(art.reading_art({"currentlyReading": "JoJolion Vol. 5"}))
        self.assertEqual(fetch.call_count, 1)

    @patch.object(art, "get_json")
    def test_jojolion_vol8_uses_verified_isbn_if_open_library_lacks_it(self, fetch):
        def fake(url, headers=None):
            if "openlibrary.org" in url:
                return {"docs": [{"title": "JoJolion Vol. 1", "cover_i": 11}]}
            if "googleapis.com" in url:
                return {"items": [{"volumeInfo": {
                    "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9784088802381"}],
                    "imageLinks": {"thumbnail": "http://books.google.com/books/content?id=abc"},
                }}]}
            self.fail("Unexpected metadata lookup " + url)
        fetch.side_effect = fake
        self.assertEqual(
            art.reading_art({"currentlyReading": "JoJolion - Hirohiko Araki", "currentlyReadingVolume": 8}),
            "https://books.google.com/books/content?id=abc",
        )

    @patch.object(art, "get_json")
    def test_edition_cover_rejects_different_isbn(self, fetch):
        fetch.return_value = {"items": [{"volumeInfo": {
            "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9784088802382"}],
            "imageLinks": {"thumbnail": "https://books.google.com/books/content?id=wrong"},
        }}]}
        self.assertIsNone(art.isbn_cover("9784088802381"))

    @patch.object(art, "get_json")
    def test_default_to_first_volume(self, fetch):
        fetch.return_value = {"docs": [
            {"title": "JoJolion Vol. 6", "cover_i": 66},
            {"title": "JoJolion Vol. 1", "cover_i": 11},
        ]}
        self.assertEqual(
            art.reading_art({"currentlyReading": "JoJolion"}),
            "https://covers.openlibrary.org/b/id/11-L.jpg",
        )

    @patch.object(art, "get_json")
    def test_default_manga_cover_when_open_library_missing(self, fetch):
        def fake(url, headers=None):
            if "openlibrary.org" in url:
                return {"docs": []}
            return {"data": [
                {
                    "title": "JoJo no Kimyou na Bouken Part 8: JoJolion",
                    "authors": [{"name": "Araki, Hirohiko"}],
                    "images": {"jpg": {"large_image_url": "https://cdn.myanimelist.net/images/manga/1/12345.jpg"}},
                },
            ]}
        fetch.side_effect = fake
        self.assertEqual(
            art.reading_art({"currentlyReading": "JoJolion - Hirohiko Araki"}),
            "https://cdn.myanimelist.net/images/manga/1/12345.jpg",
        )


if __name__ == "__main__":
    unittest.main()
