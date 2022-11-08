import configparser
import os
import xml.etree.ElementTree as ET

from ruamel import yaml

config = configparser.ConfigParser()


def load_collection():
    collection_file_key = config['general']['COLLECTION_FILE_KEY']
    collection_file_path = os.path.join(config['general']['CACHE_DIRECTORY'], f'{collection_file_key}.xml')
    collection = ET.parse(collection_file_path)
    return collection.getroot().findall('item')


def select_games(criteria, games, number_of_cards):
    """
    Select games based on criteria
    Selected cards are returned in a list
    The input games are cleared of selected games to avoid duplicates

    :param criteria: criteria to select games
    :param games: list of games to select from
    :param number_of_cards: number of cards to select
    :return: list of games left to select from
    """
    # Select cards to keep
    sorted_games = sorted(games, key=lambda x: criteria(x))
    selected_games = []
    games_to_remove = []
    for game in sorted_games:
        selected_games.append({int(game.get('objectid')): game.find('name').text})
        games_to_remove.append(game)
        if len(selected_games) == number_of_cards:
            break

    # remove all selected games from games list
    for game in games_to_remove:
        games.remove(game)

    return games, selected_games


def by_rank(x, debug=False):
    """
    Filter criteria for games ranked by bgg

    :param x: the game
    :param debug: print the value used for debugging
    :return: a value to sort by
    """
    rank_str = x.find('./boardgame/statistics/ratings/ranks/rank[@name="boardgame"]').get('value')
    if rank_str == 'Not Ranked':
        return 100000
    if debug:
        print(f"{x.get('objectid')}: {rank_str}")
    return int(rank_str)


def by_best_for_two(x, debug=False) -> float:
    """
    Filter criteria for "best for two" games
    The value is calculated using the following components:
     - the bgg vote percentage for recommended as best for two
     - the average rating
     - the max player count (lower is better)

    :param x: the game
    :param debug: print the value used for debugging
    :return: a value to sort by
    """
    try:
        max_players = int(x.find('stats').get('maxplayers'))
        rating = float(x.find('./boardgame/statistics/ratings/average').text)
        if max_players == 1:
            return 100000
        poll = x.find('./boardgame/poll[@name="suggested_numplayers"]/results[@numplayers="2"]')
        # calculate poll percentage voted best
        best = int(poll.find('result[@value="Best"]').get('numvotes'))
        rec = int(poll.find('result[@value="Recommended"]').get('numvotes'))
        not_rec = int(poll.find('result[@value="Not Recommended"]').get('numvotes'))
        total = best + rec + not_rec
        # calculate of best from total voted
        if total == 0:
            best_percentage = 0
        else:
            best_percentage = best / total
    except TypeError:
        print(f'Error parsing player count for {x.find("name").text}')
        return 100000
    if debug:
        print(f"{x.get('objectid')}: {best_percentage}, {rating / 10}, {max_players / 10}")
    return best_percentage * -1 - (rating / 10) + (max_players / 10)


def by_best_for_many(x, debug=False) -> float:
    """
    Filter criteria for "best for many" games
    :param x: the game
    :param debug: print the value used for debugging
    :return: a value to sort by
    """
    try:
        max_players = int(x.find('stats').get('maxplayers'))
        rating = float(x.find('./boardgame/statistics/ratings/average').text)
    except TypeError:
        print(f'Error parsing player count for {x.find("name").text}')
        return 100000
    if debug:
        print(f"{x.get('objectid')}: {max_players}, {rating / 10}")
    return max_players * -1 - (rating / 10)


def by_user_played_often(x, debug=False) -> float:
    """
    Filter criteria for games played often by the owner of the collection

    :param x: the game
    :param debug: print the value used for debugging
    :return: a value to sort by
    """
    try:
        user_rating = float(x.find('./numplays').text)
        rating = float(x.find('./boardgame/statistics/ratings/average').text)
    except TypeError:
        print(f'Error parsing user_rating for {x.find("name").text}')
        return 100000
    if debug:
        print(f"{x.get('objectid')}: {user_rating}, {rating / 10}")
    return user_rating * -1 - (rating / 10)


if __name__ == '__main__':
    config.read("config.ini")
    games = load_collection()
    # Remove games that are in boardgamecategory "Expansion for Base-game" (1042)
    games = [game for game in games if game.find('./boardgame/boardgamecategory[@objectid="1042"]') is None]
    # filter out games that are excluded
    excluded_games = config['select']['exclude'].split(',')
    games = [game for game in games if game.get('objectid') not in excluded_games]

    groups = {}
    games_per_group = 13
    categories = config['select']['CATEGORIES'].split(',')
    base_colors = config['select']['BASE_COLORS'].split(',')
    top_colors = config['select']['TOP_COLORS'].split(',')

    games, selected_game = select_games(by_rank, games, games_per_group)
    groups['A'] = {'category': categories[0], 'color': base_colors[0], 'top-color': top_colors[0],
                   'games': selected_game}
    games, selected_game = select_games(by_best_for_two, games, games_per_group)
    groups['B'] = {'category': categories[1], 'color': base_colors[1], 'top-color': top_colors[1],
                   'games': selected_game}
    games, selected_game = select_games(by_best_for_many, games, games_per_group)
    groups['C'] = {'category': categories[2], 'color': base_colors[2], 'top-color': top_colors[2],
                   'games': selected_game}
    games, selected_game = select_games(by_user_played_often, games, games_per_group)
    groups['D'] = {'category': categories[3], 'color': base_colors[3], 'top-color': top_colors[3],
                   'games': selected_game}

    # selection file path
    selection_file = os.path.join(config['general']['CACHE_DIRECTORY'], config['general']['SELECTION_FILE_KEY'])
    # write groups to yaml file
    with open(selection_file, 'w', encoding='utf-8') as f:
        yaml.dump({"groups": groups}, f, allow_unicode=True, default_flow_style=False)

