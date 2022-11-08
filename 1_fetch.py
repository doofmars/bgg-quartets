# coding=utf-8
import json
import configparser
import os
import csv
from time import sleep

import requests as req
import xml.etree.ElementTree as ET

config = configparser.ConfigParser()


def load_data(url, file_name):
    """
    Load data either from web or cache if already present
    :param url: url to load
    :param file_name: name of cached file
    :return: soup to parse
    """
    if not os.path.exists(config['general']['CACHE_DIRECTORY']):
        os.makedirs(config['general']['CACHE_DIRECTORY'])
    api_cache_path = os.path.join(config['general']['CACHE_DIRECTORY'], config['general']['API_CACHE_DIRECTORY'])
    if not os.path.exists(api_cache_path):
        os.makedirs(api_cache_path)
    collection_file = os.path.join(api_cache_path, file_name)
    if not os.path.exists(collection_file):
        print(f'Reading {file_name} page from web')
        response = req.get(url)
        # Check if response has yielded any game items or is in preparation state
        while response.text.find('Your request for this collection has been accepted and will be processed') > 0:
            print(f'Collection not ready yet, waiting 60 seconds')
            sleep(60)
            print(f'Reading {file_name} page from web')
            response = req.get(url)
        with open(collection_file, 'w', encoding='utf-8') as fp:
            fp.write(response.text)
            print(f'{file_name} saved to cache folder')
    else:
        print(f'Reading {file_name} from cache')

    return ET.parse(collection_file)


def get_collection():
    """
    Get the collection and convert to json
    """

    # Find table containing collection
    collection_file_key = config['general']['COLLECTION_FILE_KEY']
    url = f'https://boardgamegeek.com/xmlapi/collection/{config["fetch"]["user"]}?own=1'
    collection = load_data(url, file_name=f'{collection_file_key}.xml')

    print(f'Parsed {len(collection.getroot().findall("item"))} items, writing JSON file')
    csv_rows = []

    print(f'\nCollecting game data:')
    for game in collection.getroot().findall('item'):
        game_id = game.get("objectid")
        game_data = load_data(f'https://boardgamegeek.com/xmlapi/boardgame/{game_id}?stats=1', f'{game_id}.xml')
        game.append(game_data.getroot().find('boardgame'))
        csv_row = {
            'id': game.get('objectid'),
            'name': game.find('name').text,
            'rank': game.find('./boardgame/statistics/ratings/ranks/rank[@name="boardgame"]').get('value'),
            'yearpublished': game.find('yearpublished').text,
            'minplayers': game.find('stats').get('minplayers'),
            'maxplayers': game.find('stats').get('maxplayers'),
            'userrating': game.find('./stats/rating').get('value'),
            'numplays': game.find('numplays').text,
            'minplaytime': game.find('stats').get('minplaytime'),
            'maxplaytime': game.find('stats').get('maxplaytime'),
            'age': game.find('./boardgame/age').text,
            'weight': game.find('./boardgame/statistics/ratings/averageweight').text,
            'owned': game.find('./boardgame/statistics/ratings/owned').text,
            'bgg_usersrated': game.find('./boardgame/statistics/ratings/usersrated').text,
            'bgg_ratingavg': game.find('./boardgame/statistics/ratings/average').text,
            'bgg_ratingbay': game.find('./boardgame/statistics/ratings/bayesaverage').text,
            'image': game.find('image').text.strip(),
        }

        categories_dict = {}
        categories = game.findall('./boardgame/boardgamecategory')
        for category in categories:
            categories_dict[f'c_{category.text}'] = 'x'

        csv_row.update(categories_dict)
        csv_rows.append(csv_row)

    # Finally dump combined data as XML
    print(f'\nWriting result to XML:')
    xml_file_path = os.path.join(config['general']['CACHE_DIRECTORY'], f'{collection_file_key}.xml')
    with open(xml_file_path, 'wb') as fp:
        collection.write(fp, encoding='UTF-8')

    # Write card summary data as CSV
    print(f'\nWriting result to CSV:')
    csv_fields = []
    for row in csv_rows:
        for key in row.keys():
            if key not in csv_fields:
                csv_fields.append(key)

    csv_file_path = os.path.join(config['general']['CACHE_DIRECTORY'], f'{collection_file_key}.csv')
    with open(csv_file_path, 'w', encoding='UTF-8', newline='') as fp:
        writer = csv.DictWriter(fp, csv_fields)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f'CSV file written to cache folder')


if __name__ == '__main__':
    config.read("config.ini")
    get_collection()
