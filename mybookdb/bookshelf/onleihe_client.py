# -*- coding: latin-1 -*-
"""
client to access german Onleihe website
"""

import re
import os
import requests
import requests_random_user_agent # noqa: F401
from pathlib import Path
import urllib.parse
from django.utils.translation import gettext as _
from django.conf import settings

#from lxml import etree
import lxml.html



import logging
LOGGER = logging.getLogger(name='mybookdb.bookshelf.onleihe')

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
DUMP_RESPONSE = os.environ.get('ONLEIHE_DEBUG') in ('1',)


ONLEIHE_DETAIL_FIELDS = ( #TODO cleanup
    ['book_url', 'book_url', _("Buchdetails")],
    ['title', 'Titel'],
    ['author', 'Autor'],
    # ['translator', 'Übersetzer'],
    ['year', 'Jahr'],
    ['isbn', 'ISBN'],
    
    #['meta-keywords', 'meta-keywords', _("Suchworte")], # not available on new detail page
    #['keywords', 'keywords', _("Schlagworte")],  # == Kategorien?
    #['img_cover', 'Titelbild'],
    ['publisher', 'Verlag'],
    ['language', 'Sprache'],
    ['format', 'Format'],
    ['length', 'Umfang'],  # TODO rename pages to length (pages if ebook, duration if eaudio)
    #['filesize', 'Dateigröße'],
    #['copies', 'Exemplare'],  # <div class="exemplar-count">
    ['available', 'Verfügbar'],
    #['reservations', 'Vormerker'],
    #['available_after', 'Voraussichtlich verfügbar ab'],
    #['allow_copy', 'Kopieren'],
    ['book_description', 'book_description', _('Inhalt')],  # abstract
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

TITLE_DETAIL_PREFIX = 'Details zum Titel: '

if settings.ONLEIHE_URL:
    BASEURL = settings.ONLEIHE_URL
    assert settings.ONLEIHE_START, "missing ONLEIHE_START"
    STARTURL = f'{BASEURL}/{settings.ONLEIHE_START}'  # welcome ?
    assert settings.ONLEIHE_SEARCH, "missing ONLEIHE_SEARCH"
    SEARCHURL = f'{BASEURL}/{settings.ONLEIHE_SEARCH}'
else:
    STARTURL = None
    SEARCHURL = None
    
    
def strip_embedded_whitespaces(value):
    newvalue = value
    for ws in ('\t', '\n', '\xa0', ):
        newvalue = newvalue.replace(ws, ' ')
    newvalue = re.sub(' +', ' ', newvalue)
    return newvalue


class OnleiheClient:

    def __init__(self):
        # Start a session so we can have persistant cookies
        self.session = requests.Session()
        # self.session.headers.update(self.get_chrome_headers()) # see use of requests_random_user_agent

    def get_chrome_headers(self):
        headers = {
            'User-Agent': USER_AGENT,
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Accept-Language": "en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        }
        return headers


    def connect(self):
        """ connect to onleihe website emulating webbrowser - cookies added to requests session """
        response = self.session.get(STARTURL)
        LOGGER.debug("got cookies: %s" % self.session.cookies)  # a RequestsCookieJar
        LOGGER.debug("JSESSIONID='%s'" % (response.cookies.get('JSESSIONID')))
        assert self.session.cookies.get(
            'JSESSIONID') == response.cookies.get('JSESSIONID')
        html = response.content.decode('utf-8')
        #if not '<title>die OnleiheRegio. Startseite</title>' in html:
        if not 'title="die OnleiheRegio"' in html or 'An unexpected error has occurred!' in html:
            open('onliehe_start_bad.html', 'w').write(html)
            raise ValueError("unexpected response from onleihe url=%s." % STARTURL)
        # <section id="simple-search">
        # <h3>Einfache Suche</h3>
        if html.index('<section id="simple-search">') < 0:
            open('onliehe_missing_search.html', 'w').write(html)
            raise ValueError("missing search on onleihe page url=%s." % STARTURL)
        return
    

    def extract_mediainfo(self, html):
        """ extract media info from onleihe search result """
        media_info = []
        if html.find('mediaInfo') != -1:
            # Suchergebnisse
            LOGGER.info("extracting mediaInfo items from result")
            doc = lxml.html.document_fromstring(html)
            # <article class="list-item">
            for item in doc.xpath("//article[@class='list-item']"):
                # <a class="cover-link" title="Details zum Titel: Die Rache des Kaisers" 
                media_item = {}
                details = item.xpath("//a[@class='cover-link']")
                assert len(details) == 1, "missing article details"
                details = details[0]
                
                title = details.attrib['title']
                assert title.startswith(TITLE_DETAIL_PREFIX), "failed to extract media title"
                title = title[len(TITLE_DETAIL_PREFIX):].strip()
                media_item["title"] = title
                media_item["href"] = details.attrib['href']
                
                abstract = item.xpath("//div[@class='abstract']")
                if abstract:
                    assert len(abstract) == 1, "multiple abstracts?"
                    abstract = abstract[0]
                    media_item['abstract'] = abstract.text_content().strip()
                else:
                    media_item['abstract'] = None

                # //div[@class='media-type']
                # <svg class="svg-icon ic_ebook"><use xlink:href="#ic_ebook"></use></svg>

                author = item.xpath("//div[@class='author']")
                if author:
                    assert len(author) == 1
                    author_text = author[0].text_content().strip()
                    if author_text.startswith('Autor:'):
                        author_text = author_text[6:]
                    media_item["author"] = author_text
                else:
                    media_item["author"] = None
                    
                
                # //div[@class='available']
                # <div class="available">Verfügbar</div>
                
                media_info.append(media_item)
                                
        else:
            assert html.find('Suchergebnisse') == -1
            assert html.find('contentlist resultlist') == -1
            
        return media_info

    def extract_detailinfo(self, html):
        doc = lxml.html.document_fromstring(html)
        item = doc.xpath("//article[@class='title']")
        if len(item) == 0:
            return None
       
        details = {}
        assert len(item) == 1
        item = item[0]
        
        # fields to extract see ONLEIHE_DETAIL_FIELDS
        details['book_url'] = self.extract_detailinfo_bookurl(item)
        
        details['title'] = self.extract_detailinfo_item(item, "//div[@class='title-name']", "Titel:")
        details['subtitle'] = self.extract_detailinfo_item(item, "//div[@class='subtitle']", "Untertitel:")
        details['book_description'] = self.extract_detailinfo_item(item, "//div[@class='abstract']", "Inhalt:")
        details['author'] = self.extract_detailinfo_authors(item)
        details['publisher'] = self.extract_detailinfo_item(item, "//div[@class='publisher']", "Verlag:")
        details['year'] = self.extract_detailinfo_item(item, "//div[@class='publishing-date']", "Jahr:")
        details['language'] = self.extract_detailinfo_item(item, "//div[@class='title-language']", "Sprache:")
        details['length'] = self.extract_detailinfo_length(item)  # pages if ebook, duration [min] if eaudio
        details['available'] = self.extract_detailinfo_item(item, "//div[@class='available']", "")
        details['isbn'] = self.extract_detailinfo_item(item, "//div[@class='isbn']", "ISBN:")
        details['format'] = self.extract_detailinfo_item(item, "//div[@class='format']", "Format:")
        
        # TODO not yet extracted fields
        details['translator'] = None
        #details['keywords'] = None  # <div class="category"> ?
        
        return details
       
    def extract_detailinfo_authors(self, item):
        info_items = []
        #for info in item.xpath("//div[@class='author']"):  # fails when having more than one Author
        for info in item.xpath("//div[@class='participants']"):
            if info[0].text != 'Autor:':
                continue
                
            for author_item in info.xpath("a[@title='Alle Titel des Autors anzeigen']"):
                info_text = author_item.text.strip()
                if info_text.endswith(';'):
                    info_text = info_text[:-1]
                info_text = info_text.strip()
                #info_text = strip_embedded_whitespaces(info_text).strip()
            
                info_text = info_text.replace('\xa0', ' ')
                info_text = info_text.strip()
                info_items.append(info_text)
            
        if not info_items:
            LOGGER.warning("failed to extract authors")
        return info_items
        
    def extract_detailinfo_item(self, item, expr, prefix):
        info = item.xpath(expr)
        if info:
            info = info[0]
            label = info.xpath("span[@class='label']")
            if len(label) > 0:
                assert len(label) == 1
                label = label[0]
                label.drop_tree()
            else:
                # for class abstract have label not with <span> but with <p> - handled by prefix logic below
                pass
            
            info_text = info.text_content().strip()
            if prefix and info_text.startswith(prefix):
                info_text = info_text[len(prefix):]
            info_text = info_text.replace('\xa0', ' ')
            info_text = info_text.strip()
            return info_text
        else:
            LOGGER.info("failed to extract detailinfo item ({prefix})")
            return None
        
    def extract_detailinfo_length(self, item):
        length = self.extract_detailinfo_item(item, "//div[@class='length']", "Umfang:")
        if length:
            length = strip_embedded_whitespaces(length)
            if length.endswith(' S.'): # ebook, number of pages
                return length
            
            assert length.endswith(' min'), f"unexpected value for length: '{length}'"
            return length
        
        return None

    def extract_detailinfo_bookurl(self, item):
        link = item.xpath("//a[@class='watchlist link']")
        if len(link) > 0:
            watchlist_link = link[0].attrib["href"]
            return watchlist_link.replace('myBib', 'mediaInfo')
        else:
            LOGGER.warning("missing watchlist link in book details")
            return None

    def get_search_headers(self):
        parts = urllib.parse.urlparse(BASEURL)
        ONLEIHE_ORIGIN = f"{parts.scheme}://{parts.netloc}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "max-age=0",
            "Origin": ONLEIHE_ORIGIN,
            "Referer": STARTURL,
            # - Pragma: no-cache
        }
        return headers

    def search_book(self, search_text, field):
        data = f"""cmdId=703&sK=1000&pText=&pText={search_text}&pMediaType=-1&Suchen=Suchen"""

        response = self.session.post(
            SEARCHURL, 
            data=data.encode('utf-8'), 
            headers=self.get_search_headers(),
            )
        html = response.content.decode('utf-8')
        
        if '<title>die OnleiheRegio. Suche :  Fehler</title>' in html:
            LOGGER.error(f"error searching for '{search_text}' ({field})")
            self.dump_html('search_result_error.html', html, "error")
            return None
            
        # <title>die OnleiheRegio. Suchergebnis :  Ihre Suche nach [ Begriff: ,9783293310629] ergab 1 Titeltreffer. S. 1 (1 bis 1)</title>
        if not '<title>die OnleiheRegio. Suchergebnis :  Ihre Suche nach ' in html:
            LOGGER.error(f"search failed for '{search_text}' ({field})")
            self.dump_html('search_result_bad.html', html, "failed")
            raise RuntimeError("search failed, examine search_result_bad.html")
        
        # ... Suche nach [ Titel: xxx] ergab 3 Titeltreffer. S. 1 (1 bis 3)</title>
        match = re.search('<title>die OnleiheRegio. Suchergebnis :  Ihre Suche nach (.*?)</title>', html)
        if match is None:
            self.dump_html('search_result.html', html, "unexpected")            
            raise ValueError(f"troubles with Onleihe search / search result for '{search_text}' field={field}")
        found = match.group(1)
        # '[ Titel: Rosenthal] ergab 3 Titeltreffer. S. 1 (1 bis 3)'
        LOGGER.debug("search result: %s" % found)
        match = re.search(' ([0-9]+) Titeltreffer', found)
        if match:
            hits = int(match.group(1))
        else:
            hits = 0
        if DUMP_RESPONSE: # DEBUG:
            if hits == 1:
                self.dump_html('search_result_one.html', html, "dump")
            else:
                self.dump_html(f'search_result_{hits}.html', html, "dump")            

        # extract mediaItem info from html response
        media_info = self.extract_mediainfo(html)
        assert len(media_info) == hits, "extracted media info %s, expect %s" % (len(media_info), hits)
        return media_info
    
    def dump_html(self, dump_path, html, info="", encoding='utf-8'):
        dump_path = Path(dump_path).resolve()
        dump_path.write_text(html, encoding=encoding, errors=None)
        LOGGER.debug("HTML (%s) dumped to %s" % (info, dump_path))
            
    def get_book_details(self, book_ref):
        book_url = f'{BASEURL}/{book_ref}'
        response = self.session.get(book_url)
        assert response.status_code == 200, \
          "lookup %s failed: %s %s" % (book_ref, response.status_code, response.text)
        html = response.content.decode('utf-8')
        if not '<title>die OnleiheRegio. ' in html:
            self.dump_html('book_details_bad.html', html, 'book_details_bad')
        elif DUMP_RESPONSE:
            self.dump_html('book_details.html', html, 'book_details')
            
        # extract book details
        try:
            book_details = self.extract_detailinfo(html)
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
    if 0:
        os.environ['HTTPS_PROXY'] = os.environ['HTTP_PROXY'] = "http://127.0.0.1:8888"
    # title = 'Rosenthal'
    # title = 'Im Tal der Mangobäume'
    # title = 'Duft der Mangobäume'
    # title = 'Duft Mangobäume'
    # title = 'Mangobäume'
    # title = 'Das Erbe von Winterfell(Das Lied von Eis und Feuer  # 2)'
    # isbn = '9783293310629'
    title = 'Winterfell'
    LOGGER.info(f"search '{title}' in Onleihe catalog ...")
    try:
        client = OnleiheClient()
        client.connect()
        media_info = client.search_book(title, 'title')

        LOGGER.info("found %s items" % len(media_info))
        for item in media_info:
            LOGGER.info(" + %s," % (item.get('title'),))
        LOGGER.info('.')

    except:
        LOGGER.exception("search failed")
        sys.exit(1)
    LOGGER.info("search succeeded.")

def test_onleihe_extract():
    onleihe_response_path =  Path('onleihe_search_result.html').resolve()
    assert onleihe_response_path.is_file(), f"missing: {onleihe_response_path}"
    html = open(onleihe_response_path, 'r', encoding='utf-8').read()    
    client = OnleiheClient()
    info = client.extract_mediainfo(html)
    info = info

if __name__ == "__main__":
    DUMP_RESPONSE=1
    #test_onleihe_client()
    test_onleihe_extract()
