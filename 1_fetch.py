# coding=utf-8
import json
import os

import requests as req
from bs4 import BeautifulSoup

URL = "https://boardgamegeek.com/collection/user/Octavian?own=1"
collection_file = os.path.join('cache', 'collection.html')
collection_json = os.path.join('cache', 'collection.json')


def get_data():
    if not os.path.exists('cache'):
        os.mkdir('cache')

    if not os.path.exists(collection_file):
        print('Reading file from web')
        response = req.get(URL)
        with open(collection_file, 'w', encoding='utf-8') as fp:
            fp.write(response.text)
            print('File stored to cache')
        html = response.text
    else:
        print('Reading file from cache')
        with open(collection_file, 'r', encoding='utf-8') as fp:
            html = fp.read()

    soup = BeautifulSoup(html, 'html.parser')
    collection_table = soup.find(id='collectionitems')
    collection = list()

    # Iterate over collection table, store results to dict
    first = True
    for collection_row in collection_table.find_all('tr'):
        if first:
            first = False
            continue
        collection_item = dict()

        collection_item['name'] = collection_row.find('a', class_='primary').text
        version = collection_row.find('div', class_='geekitem_name')
        if version is not None:
            collection_item['version'] = version.text.strip()
        collection_item['year'] = collection_row.find('span', class_='smallerfont').text[1:-1]
        collection_item['id'] = collection_row.find('a', class_='primary')['href'].split('/')[2]
        user_rating = collection_row.find('div', class_='ratingtext')
        if user_rating is None:
            collection_item['user_rating'] = None
        else:
            collection_item['user_rating'] = user_rating.text

        geek_rating = collection_row.find('td', class_='collection_bggrating').text.strip()
        if geek_rating == 'N/A':
            collection_item['geek_rating'] = None
        else:
            collection_item['geek_rating'] = geek_rating
        collection_item['status'] = collection_row.find('td', class_='collection_status').text.strip()
        plays = collection_row.find('td', class_='collection_plays')
        if plays.a is None:
            collection_item['plays'] = 0
        else:
            collection_item['plays'] = int(plays.a.text)

        collection.append(collection_item)

    with open(collection_json, 'w', encoding='UTF-8') as fp:
        json.dump(collection, fp, indent=2)


if __name__ == '__main__':
    get_data()
