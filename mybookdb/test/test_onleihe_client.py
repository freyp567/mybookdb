#from django.test import TestCase
from unittest import TestCase

from bookshelf.onleihe_client import OnleiheClient, ONLEIHE_DETAIL_FIELDS
from pathlib import Path

TEST_DATA_DIR = Path('test', 'data')
TEST_DATA = [
    {
        'title': "Die Rache des Kaisers",
        'search_result': 'search_result_Rache_des_Kaisers.html',
        'detail_info':  'details_info_Rache_des_Kaisers.html',
    },
    {
        'title': "Das Spiel der Spiele",
        'detail_info': 'book_details_Wildcards.html',
    },
]


class OnleiheClientExtractTestCase(TestCase):
    def setUp(self):
        pass

    def test_extract_mediainfo(self):
        """test that we can extract book related info from search result"""
        for test_item in TEST_DATA:
            if not test_item.get('search_result'):
                continue
            
            data_path = (TEST_DATA_DIR / test_item['search_result']).resolve()
            assert data_path.is_file(), f"missing test data file: {data_path}"
            html = open(data_path, 'r', encoding='utf-8').read()
            client = OnleiheClient()
            media_info = client.extract_mediainfo(html)
            self.assertEqual(len(media_info), 1, msg="not unique or not found")
            self.assertEqual(media_info[0]['title'], test_item['title'], msg="wrong title")
            
        return            
        
    def test_extract_detailinfo(self):
        """test that we can extract book related info from search result"""
        for test_item in TEST_DATA:
            if not test_item.get('detail_info'):
                continue
            
            data_path = (TEST_DATA_DIR / test_item['detail_info']).resolve()
            assert data_path.is_file(), f"missing test data file: {data_path}"
            html = open(data_path, 'r', encoding='utf-8').read()
            client = OnleiheClient()
            details_info = client.extract_detailinfo(html)
            self.assertIsNotNone(details_info, "missing details info")
            self.assertEqual(details_info['title'], test_item['title'], msg="wrong title")
            
            # check that all required fields from ONLEIHE_DETAIL_FIELD_MAP are set
            missing = object()
            for field_info in ONLEIHE_DETAIL_FIELDS:
                field_name = field_info[0]
                field_value = details_info.get(field_name, missing)
                if field_value is missing:
                    print(f"missing field value for {field_name}")  # required?
                self.assertNotEqual(field_value, missing, f"missing field value for {field_name}")
        
        return


        
        
"""
search_text='9780061240485', field='isbn'
fails with "die OnleiheRegio, digitale Medien, Suche :  Fehler"

FUTURE, for integration test:
    href = cmedia_info[0]['href']
    details_info = client.get_book_details(href)
    assert details_info

"""