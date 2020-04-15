# -*- coding: latin-1 -*-
"""
extract book information from onleihe Merkliste saved as .html
note: set batch size to 100 to get all books on list
"""
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import csv
from argparse import ArgumentParser


BASE_URL="https://www.onleihe.de/onleiheregio/frontend/"
FIELDNAMES = ('title', 'ISBN', 'category', 'year', 'since', 'media', 'author', 'publisher', 'href', 'content',)


def extract_sibling_content(item):
    item_text = item.next_sibling
    value = str(item_text)
    return value
    

def update_media_info(item, media_item):
    item_text = item.string
    if item_text == 'Titel:':
        media_item['title'] = extract_sibling_content(item)
    elif item_text =='Untertitel:':
        subtitle = extract_sibling_content(item)
        # 'Krimilesung', 'Thriller'
        media_item['category'] = subtitle or ''
    elif item_text == 'Medientyp:':
        # eAudio, ...
        media_item['media'] = extract_sibling_content(item)
    else:
        return  # ignore


def extract_item2_content(item):
    item2 = item.parent.find('div', "item-2")
    value = item2.contents
    if len(value) > 1:
        # e.g. 'Argon Verlag', .. 'GmbH'
        pass
    value = value[0].replace('\xa0', '').strip()
    return value


def parse_german_date(value):
    try:
        dateval = datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        return ''    
    return dateval.strftime("%Y-%m-%d")
    
def update_content_info(item, media_item):
    item_text = item.string
    if item_text == 'Autor:':
        media_item['author'] = extract_item2_content(item)
    elif item_text == 'Jahr:':
        media_item['year'] = extract_item2_content(item)
    elif item_text == 'Verlag:':
        media_item['publisher'] = extract_item2_content(item)
    elif item_text == 'Im Bestand seit:':
        since = extract_item2_content(item)        
        media_item['since'] = parse_german_date(since)      
    else:
        return


def extract_item3_content(item):
    item2 = item.parent.find('div', "item-3")
    value = item2.contents
    if len(value) > 1:
        # e.g. 'Argon Verlag', .. 'GmbH'
        pass
    value = value[0].replace('\xa0', '').strip()
    return value


def update_details_info(item, media_info):
    # https://www.onleihe.de/onleiheregio/frontend/mediaInfo,0-0-357928182-200-0-0-0-0-0-0-0.html
    for link in item.find_all('a', "anchor"):
        link_title = link.get('title')
        if link_title.startswith('Details '):
            href = BASE_URL +link.get('href')
            media_info['href'] = href
            headers = {
                'User-Agent': 'Mozilla',
                'Content-Type': 'text/html; charset=utf-8',
            }
            response = requests.get(href, headers=headers)
            if response.status_code != 200:
                return
            # response.encoding = response.apparent_encoding
            details_html = response.text
            details_info = extract_details_info(details_html)
            media_info.update(details_info)
    return
    
    
def extract_details_info(html):
    details = {}
    soup = BeautifulSoup(html, features="html.parser")
    div_info =soup.find('div', class_="item-info")
    if not div_info:        
        return details
    for child in div_info.find_all('div', class_="item-2", recursive=True):
        # eAudio: 'Sprache:', 'Format:', 'Dauer:'; eBook: 'Format:', Umfang:', 'Reihe:'
        if 'ISBN' in str(child):
            details['ISBN'] = extract_item3_content(child)
    for child in div_info.find_all('div', class_="item-1", recursive=True):
        h3 = child.find('h3')
        if not h3:
            continue
        heading = h3.contents[0]
        if heading == 'Kategorie:':
            continue  # TODO extract
        elif heading =='Inhalt:':
            content = extract_item2_content(child)
            # formatting in content? need to normalize??
            details['content'] = content
        else:
            continue
    return details
    

def extract_media_item(item):
    media_item = {}
    for child_item in item.find_all('span', "hidden"):
        update_media_info(child_item, media_item)

    for child_item in item.find_all('div', "item-1", recursive=True):
        update_content_info(child_item, media_item)
        
    child_item =item.find('div', "l-row")
    if child_item:
        update_details_info(child_item, media_item)
                
    return media_item

    
def extract_items(html):
    soup = BeautifulSoup(html, features="html.parser")
    
    # div class='media-item'
    media_items = soup.find_all('div', "media-item")
    all_items = []
    for item in media_items:
        media_item = extract_media_item(item)                    
        all_items.append(media_item)
    return all_items


def dump_watchlist_onleihe(items, csv_path):
    keys = set()
    for row in items:
        keys.update(row.keys())
    delta = keys.difference(set(FIELDNAMES))
    if delta:
        delta = delta
    with csv_path.open('w', encoding='utf-8-sig') as csv_file:
        # latin-1 -> UnicodeEncodeError: 'latin-1' codec can't encode character '\u0308' in position 69: ordinal not in range(256)
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES, restval="", extrasaction="ignore", dialect="excel")
        writer.writeheader()
        for row in items:
            writer.writerow(row)
    return


def load_watchlist(csv_path):
    items = []
    with csv_path.open('r', encoding='utf-8-sig') as csv_file:
        # latin-1 -> UnicodeEncodeError: 'latin-1' codec can't encode character '\u0308' in position 69: ordinal not in range(256)
        reader =  csv.DictReader(csv_file, restkey="extra", restval="", dialect="excel")
        row_count = 0
        for row in reader:
            row = dict(row)
            row_count += 1
            assert not row.get("extra")
            items.append(row)
    return items


def getArgParser():
    parser = ArgumentParser()
    parser.add_argument("path", type=Path)
    return parser

def main():
    args = getArgParser().parse_args()
    watchlist_path = args.path
    csv_path = watchlist_path.parent / 'watchlist_onleihe.csv'
    
    if 1: # shortcut for debugging
        watchlist_items = load_watchlist(csv_path)
        print("loaded %s media items" % len(watchlist_items))
        
    else:
        print("extract media items from %s" % watchlist_path)
        html = watchlist_path.open('r', encoding='utf-8').read()
        if 'Bitte wählen Sie Ihre Bibliothek aus' in html:
            raise RuntimeError("not loggedin")
        
        watchlist_items = extract_items(html)        
        print("extracted %s media items" % len(watchlist_items))

    dump_watchlist_onleihe(watchlist_items, csv_path)
    print("output media items to %s" % csv_path)
    
    # TODO serialize to same .csv format as MyBookDroid ? (for import there)
    # or different format / app
        
    return

main()

