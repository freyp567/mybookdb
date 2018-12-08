# -*- coding: latin-1 -*-
"""
client to access german Onleihe website
"""

import re
import requests
from pathlib import Path
import urllib.parse
from django.utils.translation import gettext as _

from bookshelf.onleihe_bookdetails_parser import OnleiheBookDetailsParser

import logging
LOGGER = logging.getLogger(name='mybookdb.bookshelf.onleihe')

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
DUMP_RESPONSE = False


ONLEIHE_DETAIL_FIELDS = (
    ['book_url', 'book_url', _("Buchdetails")],
    ['title', 'Titel'],
    ['author', 'Autor'],
    ['translator', 'Übersetzer'],
    ['year', 'Jahr'],
    ['isbn', 'ISBN'],
    
    ['meta-keywords', 'meta-keywords', _("Suchworte")],
    ['keywords', 'keywords', _("Schlagworte")],
    #['img_cover', 'Titelbild'],
    ['publisher', 'Verlag'],
    ['language', 'Sprache'],
    ['format', 'Format'],
    ['pages', 'Umfang'],
    #['filesize', 'Dateigröße'],
    ['copies', 'Exemplare'],
    ['available', 'Verfügbar'],
    #['reservations', 'Vormerker'],
    #['available_after', 'Voraussichtlich verfügbar ab'],
    #['allow_copy', 'Kopieren'],
    ['book_description', 'book_description', _('Inhalt')],
)

ONLEIHE_DETAIL_FIELD_MAP = {}
for item in ONLEIHE_DETAIL_FIELDS:
    if len(item) == 1:
        field_name = item[0]
        item.append(field_name, field_name, _(field_name))
        ONLEIHE_DETAIL_FIELD_MAP[field_name] = field_name
    elif len(item) == 2:
        field_name, field_title = item
        ONLEIHE_DETAIL_FIELD_MAP[field_title] = field_name
        field_title_loc = _(field_title)
        item.append(field_title_loc)


class OnleiheClient:

    onleihe = 'www4.onleihe.de'
    baseurl = f'{onleihe}/onleiheregio/frontend'
    starturl = f'http://{baseurl}/welcome,51-0-0-100-0-0-1-0-0-0-0.html'
    #searchurl = f'http://{baseurl}/search,0-0-0-100-0-0-0-0-0-0-0.html'
    searchurl = f'http://{baseurl}/search,0-0-0-0-0-0-0-0-0-0-0.html'
    # TODO derive from settings.ONLEIHE_URL

    def __init__(self):
        # Start a session so we can have persistant cookies
        self.session = requests.Session()
        self.session.headers.update(self.get_chrome_headers())

    def get_chrome_headers(self):
        return {
            'User-Agent': USER_AGENT,
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Accept-Language": "en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        }


    def connect(self):
        """ connect to onleihe website emulating Chrome browser """
        response = self.session.get(self.starturl)
        LOGGER.debug("got cookies: %s" % self.session.cookies)  # a RequestsCookieJar
        LOGGER.debug("JSESSIONID='%s'" % (response.cookies.get('JSESSIONID')))
        assert self.session.cookies.get(
            'JSESSIONID') == response.cookies.get('JSESSIONID')
        html = response.content.decode('utf-8')
        assert '<title>die OnleiheRegio. Startseite</title>' in html
        # <img .*?src="(?url [^"]*)".*?/>
        """
        # see 'var lwa = trackPage()' embedded in html
        # http://www4.onleihe.de/onleiheregio/static/js/globals.js
        # http://statistik.onleihe.de/statistics/lwa.js
        #    function lgSet_Cookie
        # http://statistik.onleihe.de/statistics/includes/trackPage.php?conf=LWA_p93&lwa_id=LWA_p93&referrer=&visitorid=18998590032&sessionid=25879500810&newses=1&trackermode=undefined&w=1920&h=1080&cd=24&docTitle=die%20OnleiheRegio.%20Startseite
        # request Cookie: Logaholic_Screenres=50284383836

        """

    def extract_mediainfo(self, html):
        media_info = []
        item_set = set()
        if html.find('mediaInfo') != -1:
            # extract book items from res_html
            # Suchergebnisse
            # <div class="box contentlist resultlist">
            LOGGER.info("extracting mediaInfo items from result")
            # <a class="img-anchor" title="Details zum Titel: Die Akte Rosenthal - Teil 2" href="mediaInfo,0-0-542064265-200-0-0-0-0-0-0-0.html">
            for match in re.finditer('<a (.*?)>', html):
                anchor = match.group(0)
                if 'mediaInfo' in anchor:
                    match2 = re.search('title="(.*?)" href="(.*?)"', match.group(1))
                    title = match2.group(1)
                    TITLE_DETAIL_PREFIX = 'Details zum Titel: '
                    if title.startswith(TITLE_DETAIL_PREFIX):
                        title = title[len(TITLE_DETAIL_PREFIX):]
                    href = match2.group(2)
                    if href not in item_set:
                        item_set.add(href)
                        media_item = {
                            'title': title,
                            'href': href,
                        }
                        media_info.append(media_item)
                else:
                    # LOGGER.debug("link ignored: %s" % anchor)
                    pass
        else:
            assert html.find('Suchergebnisse') == -1
            assert html.find('contentlist resultlist') == -1
            
        return media_info


    def get_search_headers(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "max-age=0",
            "Origin": f"http://{self.onleihe}",
            "Referer": self.searchurl,
            # - Pragma: no-cache
        }
        return headers

    def search_book(self, book_title='', isbn=''):
        assert book_title or isbn, "either book_title or isbn must be specified for search"
        data = f"""cmdId=701&sK=1000&pText=&pTitle={book_title}&pAuthor=&pKeyword=&pisbn={isbn}&ppublishdate=&pMediaType=-1&pLang=-1&pPublisher=-1&pCategory=-1&SK=1000&pPageLimit=20&Suchen=Suchen"""
        # session_id = self.session.cookies.get('JSESSIONID')
        self.session.cookies.set(name='test', value='1')

        response = self.session.post(
            self.searchurl, 
            data=data.encode('utf-8'), 
            headers=self.get_search_headers(),
            )
        html = response.content.decode('utf-8')
        if not '<title>die OnleiheRegio. Suchergebnis :  Ihre Suche nach ' in html:
            self.dump_html('check_search_result.html', html, "check")
        # ... Suche nach [ Titel: Rosenthal] ergab 3 Titeltreffer. S. 1 (1 bis 3)</title>
        if book_title:
            book_title = urllib.parse.quote(book_title)
        match = re.search('<title>die OnleiheRegio. Suchergebnis :  Ihre Suche nach (.*?)</title>', html)
        if match is None:
            raise ValueError("troubles with Onleihe search / search result")
        found = match.group(1)
        # '[ Titel: Rosenthal] ergab 3 Titeltreffer. S. 1 (1 bis 3)'
        LOGGER.info("search result: %s" % found)
        if False: # DEBUG:
            Path('./search_result.html').write_text(html)

        # extract mediaItem info from html response
        return self.extract_mediainfo(html)
    
    def dump_html(self, dump_path, html, info="", encoding='utf-8'):
        dump_path = Path(dump_path).resolve()
        dump_path.write_text(html, encoding=encoding, errors=None)
        LOGGER.debug("HTML (%s) dumped to %s" % (info, dump_path))
            
    def get_book_details(self, book_ref):
        book_url = f'http://{self.baseurl}/{book_ref}'
        response = self.session.get(book_url)
        assert response.status_code == 200, \
          "lookup %s failed: %s %s" % (book_ref, response.status_code, response.text)
        html = response.content.decode('utf-8')
        assert '<title>die OnleiheRegio. ' in html
        if DUMP_RESPONSE:
            self.dump_html('book_details.html', html, 'book_details')
            
        # extract book details
        try:
            parser = OnleiheBookDetailsParser()
            parser.feed(html)
            book_details = parser.get_info()
            info = {"book_url": book_url}
            for field_title, field_value in book_details.items():
                # normalize display oriented titles to field names
                field_name = ONLEIHE_DETAIL_FIELD_MAP.get(field_title)
                if not field_name:
                    # have no mapping, use title
                    #ä e.g. 'meta-keywords', 'img_cover', ...
                    field_name = field_title
                info[field_name] = field_value
                
        except:
            self.dump_html('book_details_error.html', html, 'book_details')
            LOGGER.exception("failed to extact book details, see book_details_error.html")
            raise RuntimeError("filed to extract book details from %s" % book_ref)

        return info
        

def test_onleihe_client():
    if 1:
        os.environ['HTTPS_PROXY'] = os.environ['HTTP_PROXY'] = "http://127.0.0.1:8888"
    # title = 'Rosenthal'
    # title = 'Im Tal der Mangobäume'
    # title = 'Duft der Mangobäume'
    # title = 'Duft Mangobäume'
    # title = 'Mangobäume'
    # title = 'Das Erbe von Winterfell(Das Lied von Eis und Feuer  # 2)'
    title = 'Winterfell'
    LOGGER.info("search title in Onleihe catalog ...")
    try:
        client = OnleiheClient()
        client.connect()
        media_info = client.search_book(title)

        LOGGER.info("found %s items" % len(media_info))
        for item in media_info:
            LOGGER.info(" + %s," % (item.get('title'),))
        LOGGER.info('.')

    except:
        LOGGER.exception("search failed")
        sys.exit(1)
    LOGGER.info("search succeeded.")

if __name__ == "__main__":
    test_onleihe_client()
