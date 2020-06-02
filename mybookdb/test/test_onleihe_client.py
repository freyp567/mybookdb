#from django.test import TestCase
from unittest import TestCase

from bookshelf.onleihe_client import OnleiheClient, ONLEIHE_DETAIL_FIELDS
from pathlib import Path

TEST_DATA_PATH = Path('test', 'data', 'search_result_Rache_des_Kaisers.html')
TEST_DATA_TITLE = "Die Rache des Kaisers"


class OnleiheClientExtractTestCase(TestCase):
    def setUp(self):
        pass

    def test_extract(self):
        """test that we can extract book related info from search result"""
        data_path = TEST_DATA_PATH.resolve()
        assert data_path.is_file(), f"missing test data file: {data_path}"
        html = open(TEST_DATA_PATH, 'r', encoding='utf-8').read()
        client = OnleiheClient()
        media_info = client.extract_mediainfo(html)
        self.assertEqual(len(media_info), 1, msg="not unique or not found")
        self.assertEqual(media_info[0]['title'], TEST_DATA_TITLE, msg="wrong title")
        