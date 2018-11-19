# -*- coding: latin-1 -*-
"""
HTML Parser to extract book details info from onleihe book details page
"""
#https://www.pythoncentral.io/html-parser/

# TODO extract book description from
# <div class="item-1"><h3>Inhalt:</h3></div>


import sys
from html.parser import HTMLParser
import urllib.request as urllib2
from pathlib import Path


class OnleiheBookDetailsParser(HTMLParser):
    
    def __init__(self, **kwargs):
        super(OnleiheBookDetailsParser, self).__init__(**kwargs)
        self.context = None
        self.prop_name = ''
        self.prop_value = ''
        self.props = {}
        self.ignored = set()
        self.keywords = None
        self.keywords_text = ''
        self.keywords_status = -1
        self.path = []
        
        
    def set_props(self, key, value):
        assert not key in self.props 
        if key in ('Exemplare', 'Verfügbar', 'Vormerker'):
            if value.startswith('('):
                value = int(value[1:-1])
        self.props[key] = value


    def handle_starttag(self, startTag, attrs):
        self.path.append(startTag)
        xattrs = dict(attrs)
        elmt_class = xattrs.get('class')
        if startTag == 'a':
            if self.keywords_status == 2:
                self.keywords.append(self.keywords_text.strip()[:-1])
                self.keywords_text = ''
            if self.keywords_status == 1:
                self.keywords_status = 2
            return
        elif startTag == 'div':
            if self.context == 'book-description':
                if elmt_class == "item-2": # start of book description
                    self.keywords_status = 2
                elif elmt_class == "item-3": # end of book description
                    self.keywords_status = 0
                else:
                    elmt_clas = elmt_class  # what else?
                # remaining handled by handle_endtag
            elif elmt_class == 'item-keywords':
                self.keywords = []
                self.keywords_text = ''
                self.keywords_status = 1
            elif elmt_class == 'item-2':
                self.context = 'item-2'
                self.prop_name = ''
            elif elmt_class == 'item-3':
                self.context = 'item-3'
                self.prop_value = ''
                if self.keywords_status > 0 and self.keywords_text:
                    self.keywords.append(self.keywords_text.strip()[:-1])
                    self.keywords_status = 0
                    self.set_props('keywords', self.keywords)
            else:
                pass
        else:
            if elmt_class == 'item-2':
                self.test = 'item-2'
            elif elmt_class == 'item-3':
                self.test = 'item-3'
            pass  # title, 
        pass #self.lsStartTags.append(startTag)


    def handle_data(self, data):
        if data == 'Inhalt:' and self.path[-1] in ('h3',): 
            # preceedes book description
            self.keywords_text = ''
            self.keywords_status = 1
            self.context = "book-description"
            self.prop_name = "book_description"
            return
        if 'Familensaga' in data:  # Apfelplantage 
            data = data  # TODO book description
        if self.keywords_status == 2:
            self.keywords_text += data
            return
        if self.context == 'item-2':
            self.prop_name += data
        elif self.context == 'item-3':
            self.prop_value += data
        
        
    def handle_endtag(self, endTag):
        startTag = self.path.pop()
        if endTag == 'a' and self.keywords_status == 1:
            self.keywords.append(self.keywords_text)
            self.keywords_text = ''
            
        elif endTag == 'div' and self.context == 'book-description':
            if self.keywords_status == 2:
                prop_value = self.keywords_text.strip()
                assert prop_value, "expect non-empty book description"
                self.set_props('book_description', prop_value)
                self.keywords_status = 0  # consumed
                self.context = None
            else:
                print("scanning book description") # scanning start/end of book description
        
        elif endTag == 'div' and self.context:
            if self.context == 'item-2':
                self.prop_name = self.prop_name.strip()
            elif self.prop_name:  # self.context == 'item-3':
                if self.prop_name in ('Autor:', 'Format:', 'Titel:', 'Jahr:', 'Verlag:', 
                                      'Sprache:', 'ISBN:', 'Übersetzer:', 'Umfang:', 'Dateigröße:', 
                                      'Exemplare:', 'Verfügbar:', 'Vormerker:',
                                      'Voraussichtlich verfügbar ab:',
                                      'Kopieren:', 
                                      ):
                    prop_name = self.prop_name[:-1]
                    prop_value = self.prop_value.replace('\xa0', ' ').strip()
                    self.set_props(prop_name, prop_value)
                elif self.prop_name in (
                    'Verbundteilnehmer', 'Startseite', 
                    'Kinderbibliothek, Titelanzahl:',
                    ):
                    pass  # silently ignore
                elif 'Titelanzahl:' in self.prop_name:
                    pass
                elif self.prop_name.endswith(':'):  
                    # e.g. 'Geeignet für:', 'Max. Ausleihdauer:', ...
                    # print('ignored: %s = %s' % (self.prop_name, self.prop_value))
                    self.ignored.add(self.prop_name)
                elif self.prop_value == '\xa0':
                    pass
                else:
                    # print('ignored: %s = %s' % (self.prop_name, self.prop_value))
                    self.ignored.add(self.prop_name)
                self.context = None
                self.prop_name = ''
                self.prop_value = ''
            self.context = None

    def handle_startendtag(self, startendTag, attrs):
        xattrs = dict(attrs)
        if startendTag == 'meta':
            # {'http-equiv': 'Content-Type', 'content': 'text/html; charset=UTF-8'}
            # {'name': 'keywords', 'content': 'die OnleiheRegio, digitale Medien, Der Ruf der Bäume'}
            #
            if xattrs.get('name') == 'keywords':
                self.set_props('meta-keywords', xattrs.get('content').split(', '))
        elif startendTag == 'img':
            if 'Vergrößerte Darstellung Cover:' in xattrs.get('alt'):
                self.set_props('img_cover', xattrs.get('src'))
        else:
            assert startendTag in ('link', 'hr', 'input', 'br')

    def handle_comment(self, data):
        pass #self.lsComments.append(data)

    def get_info(self):
        return self.props
    
"""
        <h2>Informationen zum Titel ...
        <span class="hidden">Medientyp:</span>eBook</div>
        <img alt="Vergrösserte Darstellung Cover: Der Ruf der Bäume. Externe Website (neues Fenster)"
 	 src="https://static.onleihe.de/images/randomhousebook/20170110/9783641191702/tn9783641191702s.jpg"/>

<div class="item-2">Titel:</div>
<div class="item-3">Der Ruf der BÃ¤ume</div>
..
<div class="item-1">&nbsp;</div><div class="item-2">&nbsp;</div>        
<div class="item-3">Roman</div>

<div class="item-2">Autor:</div>
<div class="item-3">
<a class="anchor" title="Alle Titel des Autors anzeigen" href="simpleMediaList,0-0-521358461-103-0-0-0-0-0-20768479-0.html"
		>Chevalier, Tracy
</a>
&nbsp;</div>

<div class="item-2">Jahr:</div>              
<div class="item-3">2017</div></div>

<div class="item-2">Verlag:</div>
<div class="item-3"><a class="anchor" title="Alle Titel des Verlags anzeigen" href="simpleMediaList,0-0-0-105-0-0-0-0-0-42571497-0.html">Knaus</a></div></div>

<div class="item-2"><abbr lang="de" title="Internationale Standardbuchnummer" >ISBN</abbr>:</div>
<div class="item-3">9783641191702</div></div>

<div class="item-2">Format:</div>			        
<div class="item-3"><div>ePub</div></div></div>

<div class="item-keywords">
<div class="item-1"><h3>Kategorie:</h3></div>
<div class="item-2"><div class="item-3-0">
<a class="anchor" href="mediaList,0-2-0-101-0-0-0-0-0-0-0.html" title="Alle Titel zu dieser Kategorie anzeigen">
  Belletristik &amp; Unterhaltung</a>/
<a class="anchor" href="mediaList,0-160-0-101-0-0-0-0-0-0-0.html" title="Alle Titel zu dieser Kategorie anzeigen">
  Romane &amp; ErzÃ¤hlungen</a>/
<a class="anchor" href="mediaList,0-616-0-101-0-0-0-0-0-0-0.html" title="Alle Titel zu dieser Kategorie anzeigen">
  Historisches</a></div></div>

<div class="item-1"><h3>Inhalt:</h3></div>
<div class="item-2">Auf der Suche nach einer neuen Heimat - die große Familiensaga von Tracy Chevalier Amerika, Mitte des 19. Jahrhunderts: Die Goodenoughs trÃ¤umen von fruchtbarem Ackerland im Westen, bleiben aber mit ihrem Planwagen klÃ¤glich im Sumpfland von Ohio stecken. Der verzweifelte Versuch, hier eine Apfelplantage anzulegen, endet tragisch. Fasziniert von ErzÃ¤hlungen Ã¼ber BÃ¤ume, die angeblich in den Himmel wachsen, zieht der jÃ¼ngste Sohn Robert weiter westwÃ¤rts, bis nach Kalifornien. Doch am Ziel seiner TrÃ¤ume wird er von seiner tragischen Familiengeschichte eingeholt.</div>

<div class="item-1"><h3>Autor(en) Information:</h3></div>
<div class="item-2">Die Amerikanerin Tracy Chevalier, Jahrgang 1962, hat bisher acht historische Romane geschrieben. Ihr zweiter, &#034;Das MÃ¤dchen mit dem Perlenohrring&#034;, wurde zum Weltbestseller und mit Scarlett Johansson und Colin Firth in den Hauptrollen verfilmt. &#034;Der Ruf der BÃ¤ume&#034; ist nach &#034;Zwei bemerkenswerte Frauen&#034; und &#034;Die englische Freundin&#034; ihr dritter Roman bei Knaus. Tracy Chevalier lebt mit ihrer Familie in London.</div>
<div class="item-3">&nbsp;</div>     
     
<div class="item-2"><span title="Zeigt die Anzahl der Vormerker auf diesen Titel">
Vormerker</span>:</div>
<div class="item-3">(0)</div>

<div class="item-2">Voraussichtlich verfÃ¼gbar ab:</div>
<div class="item-3">sofort</div>     
"""

def test_onleihe_bookdetails_parser(args=sys.argv[1:]):
    if args:
        assert len(args) == 1
        test_data_path = args[0]
    else:
        test_data_path = "../book_details.html"
    test_data_path = Path(test_data_path)
    test_data_path = test_data_path.resolve()
    assert test_data_path.exists(), "missing input data: %s" % test_data_path
    
    html = test_data_path.read_text(encoding='latin-1') # errors=
    parser = OnleiheBookDetailsParser(convert_charrefs=True)  
    parser.feed(html)
    info = parser.get_info()
    
    for key, value in info.items():
        print('%s = %s' % (key, repr(value)))
    print('.')

if __name__ == "__main__":
    test_onleihe_bookdetails_parser()
