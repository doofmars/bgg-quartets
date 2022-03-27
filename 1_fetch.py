# coding=utf-8
import json
import os
import configparser
from types import NoneType

import requests as req
from bs4 import BeautifulSoup, Tag

config = configparser.ConfigParser()


def load_data(url, file_name):
    """
    Load data either from web or cache if already present
    :param url: url to load
    :param file_name: name of cached file
    :return: soup to parse
    """
    if not os.path.exists(config['fetch']['CACHE_DIRECTORY']):
        os.mkdir(config['fetch']['CACHE_DIRECTORY'])
    collection_file = os.path.join(config['fetch']['CACHE_DIRECTORY'], file_name)
    if not os.path.exists(collection_file):
        print(f'Reading {file_name} page from web')
        response = req.get(url)
        with open(collection_file, 'w', encoding='utf-8') as fp:
            fp.write(response.text)
            print(f'{file_name} saved to cache folder')
        html = response.text
    else:
        print(f'Reading {file_name} from cache')
        with open(collection_file, 'r', encoding='utf-8') as fp:
            html = fp.read()
    if file_name.endswith('html'):
        return BeautifulSoup(html, 'html.parser')
    if file_name.endswith('xml'):
        return BeautifulSoup(html, 'lxml')


def get_collection():
    """
    Get the collection and convert to json
    """

    # Find table containing collection
    collection_file_key = config['fetch']['COLLECTION_FILE_KEY']
    collection_table = load_data(config['fetch']['URL'], file_name=f'{collection_file_key}.html').find(id='collectionitems')
    collection = list()

    # Iterate over collection table, store results to dict
    first = True
    for collection_row in collection_table.find_all('tr'):
        # Skip header, we don't care about this
        if first:
            first = False
            continue
        # Append parsed collection row to collection list for later dumping
        collection.append(parse_collection_row(collection_row))

    print(f'Parsed {len(collection)} items, writing JSON file')

    print(f'\nCollecting game data:')
    for game in collection:
        game_id = game.get("id")
        game_data = load_data(f'https://boardgamegeek.com/xmlapi/boardgame/{game_id}?stats=1', f'{game_id}.xml')
        game['boardgamecategory'] = [category.text for category in game_data.find_all('boardgamecategory')]
        game['boardgamesubdomain'] = [domain.text for domain in game_data.find_all('boardgamesubdomain')]
        game['image'] = tex_or_none(game_data.find('image')).strip()
        game['minplayers'] = tex_or_none(game_data.find('minplayers'))
        game['maxplayers'] = tex_or_none(game_data.find('maxplayers'))
        game['playingtime'] = tex_or_none(game_data.find('playingtime'))
        suggested_numplayers = parse_poll(game_data.find('poll', attrs={"name": "suggested_numplayers"}))
        game['best_minplayers'] = map_poll(suggested_numplayers, is_best)[0]
        game['best_maxpleyers'] = map_poll(suggested_numplayers, is_best)[-1]
        game['best_numplayers'] = map_poll(suggested_numplayers, is_best)
        game['recommended_numplayers'] = map_poll(suggested_numplayers, is_recommended)

    # Finally dump data as JSON
    print(f'\nWriting result to JSON:')
    with open(os.path.join(config['fetch']['CACHE_DIRECTORY'], f'{collection_file_key}.json'), 'w', encoding='UTF-8') as fp:
        json.dump(collection, fp, indent=2)

    print(f'JSON file written to cache folder')


def parse_collection_row(collection_row):
    """
    Parse a single collection table row into a dict
    :param collection_row: the row to parse
    :return: a dictionary containing row values
    """
    collection_item = dict()
    collection_item['name'] = collection_row.find('a', class_='primary').text
    version = collection_row.find('div', class_='geekitem_name')
    if version is not None:
        collection_item['version'] = version.text.strip()
    collection_item['year'] = collection_row.find('span', class_='smallerfont').text[1:-1]
    collection_item['id'] = collection_row.find('a', class_='primary')['href'].split('/')[2]
    collection_item['user_rating'] = tex_or_none(collection_row.find('div', class_='ratingtext'))
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
    return collection_item


def map_poll(poll, check):
    """
    Map the voting poll results dict to a list containing only voting options that pass the check
    :param poll: The voting poll consisting of vote topic with recommendations by the community
    :param check: Checking function to validate against
    :return: None if nothing is recommended or a list of recommended player numbers.
    """
    try:
        recommended = [vote_option for (vote_option, votes) in poll.items() if check(votes)]
    except KeyError:
        return [None]
    if len(recommended) == 0:
        return [None]
    else:
        return recommended


def is_best(votes):
    return int(votes['Best']) >= int(votes['Recommended']) + int(votes['Not Recommended'])


def is_recommended(votes):
    return int(votes['Best']) + int(votes['Recommended']) >= int(votes['Not Recommended'])


def tex_or_none(tag):
    if tag is None:
        return None
    else:
        return tag.text


def parse_poll(poll_data):
    if poll_data is None:
        return None
    else:
        poll = dict()
        results = poll_data.find_all('results')
        for result in results:
            poll[result['numplayers']] = {
                str(child['value']): child['numvotes']
                for child in result.children
                if isinstance(child, Tag)
            }
        return poll


if __name__ == '__main__':
    config.read("config.ini")
    get_collection()
