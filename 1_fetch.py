# coding=utf-8
import os

import requests as req
from bs4 import BeautifulSoup

URL = "https://boardgamegeek.com/collection/user/Octavian?own=1"
collection_file = os.path.join('cache', 'collection.html')


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
    first = True
    for collection_item in collection_table.find_all('tr'):
        if first:
            first = False
            continue
        print(collection_item)
        break


if __name__ == '__main__':
    get_data()
