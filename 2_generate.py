import configparser
import json
import os
import sys

from PIL import Image, ImageDraw

config = configparser.ConfigParser()


def load_data():
    """
    Load data cache

    :return: soup to parse
    """
    if not os.path.exists(config['generate']['CARD_CACHE']):
        os.mkdir(config['generate']['CARD_CACHE'])
    collection_file_key = config['fetch']['COLLECTION_FILE_KEY']
    collection_file = os.path.join(config['fetch']['RESULT_DIRECTORY'], f'{collection_file_key}.json')
    if not os.path.exists(collection_file):
        raise FileNotFoundError('Missing collection_file')
    else:
        print(f'Reading {collection_file} from cache')
        with open(collection_file, 'r', encoding='utf-8') as fp:
            return json.load(fp)


def generate_cards():
    collection = load_data()
    for game in collection:
        render_as_card(game)
        break


def render_as_card(game_data):
    pass


if __name__ == '__main__':
    config.read("config.ini")
    generate_cards()
