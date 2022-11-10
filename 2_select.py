import os
import xml.etree.ElementTree as ET

from ruamel import yaml

config = yaml.safe_load(open('config.yaml', 'r', encoding='utf-8'))


def load_collection():
    collection_file_key = config['general']['collection_file_key']
    collection_file_path = os.path.join(config['general']['cache_directory'], f'{collection_file_key}.xml')
    collection = ET.parse(collection_file_path)
    return collection.getroot().findall('item')


def compact_range(min_value, max_value):
    """
    Compare the input values, if both are the same only return one value

    :param min_value: minimum playtime
    :param max_value: maximum playtime
    """
    if min_value == max_value:
        return min_value
    else:
        return f'{min_value}-{max_value}'


def compact_number(number: int) -> str:
    """
    Return a compact number, this will return a number with a suffix like k, M

    :param number: the number to compact
    """
    if number < 1000:
        return str(number)
    elif number < 1000000:
        return f'{number // 1000}K'
    else:
        return f'{number // 1000000}M'


def compact_poll_result(poll_results) -> str:
    """
    Compact the poll result
    Calculate the recommended player count and best player count from poll results

    :param poll_results: The poll result to compact
    """
    recommended = []
    best = []
    for results in poll_results:
        result_options = results.findall('result')
        total_votes = 0
        for result_option in result_options:
            total_votes += int(result_option.get('numvotes'))
        voted_best = int(results.find('result[@value="Best"]').get('numvotes'))
        voted_recommended = int(results.find('result[@value="Recommended"]').get('numvotes'))
        if total_votes / 2 < voted_best:
            best.append(results.get('numplayers'))
            recommended.append(results.get('numplayers'))
        if total_votes / 2 < voted_recommended + voted_best:
            recommended.append(results.get('numplayers'))

    if group_to_str(best) == group_to_str(recommended):
        return f'{group_to_str(best)}'
    else:
        return f'{group_to_str(recommended)} / {group_to_str(best)}'


def group_to_str(recommended):
    """
    Convert a list of numbers to a string with ranges
    :param recommended: The list of numbers
    """
    if len(recommended) == 0:
        return '-'
    if len(recommended) == 1:
        return str(recommended[0])
    else:
        return compact_range(recommended[0], recommended[-1])


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
        poll_results = game.findall('./boardgame/poll[@name="suggested_numplayers"]/results')
        selected_games.append({
            '_id': game.get('objectid'),
            'name': game.find('name').text,
            'image': game.find('image').text,

            'year': game.find('yearpublished').text,
            'playtime': compact_range(game.find('stats').get('minplaytime'), game.find('stats').get('maxplaytime')),
            'rating': f"{float(game.find('./boardgame/statistics/ratings/average').text):.2f}",
            'owners': compact_number(int(game.find('./boardgame/statistics/ratings/owned').text)),
            'weight': f"{float(game.find('./boardgame/statistics/ratings/averageweight').text):.2f}",

            'players': compact_range(game.find('stats').get('minplayers'), game.find('stats').get('maxplayers')),
            'players_recommended': compact_poll_result(poll_results),
            'age': f"{game.find('./boardgame/age').text}+",
            'user_rating': game.find('./stats/rating').get('value'),
            'user_play_count': int(game.find('numplays').text)
        })
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
    games = load_collection()
    # Remove games that are in boardgamecategory "Expansion for Base-game" (1042)
    games = [game for game in games if game.find('./boardgame/boardgamecategory[@objectid="1042"]') is None]
    # filter out games that are excluded
    excluded_games = config['select']['exclude']
    games = [game for game in games if game.get('objectid') not in excluded_games]

    groups = {}
    games_per_group = 13
    categories = config['select']['categories']
    base_colors = config['select']['base_colors']
    top_colors = config['select']['top_colors']

    games, selected_game = select_games(by_rank, games, games_per_group)
    groups['A'] = {'category': categories[0],
                   'color': base_colors[0],
                   'top-color': top_colors[0],
                   'games': selected_game}
    games, selected_game = select_games(by_best_for_two, games, games_per_group)
    groups['B'] = {'category': categories[1],
                   'color': base_colors[1],
                   'top-color': top_colors[1],
                   'games': selected_game
                   }
    games, selected_game = select_games(by_best_for_many, games, games_per_group)
    groups['C'] = {'category': categories[2],
                   'color': base_colors[2],
                   'top-color': top_colors[2],
                   'games': selected_game
                   }
    games, selected_game = select_games(by_user_played_often, games, games_per_group)
    groups['D'] = {'category': categories[3],
                   'color': base_colors[3],
                   'top-color': top_colors[3],
                   'games': selected_game
                   }

    # selection file path
    selection_file = os.path.join(config['general']['cache_directory'], config['general']['selection_file_key'])
    # write groups to yaml file
    with open(selection_file, 'w', encoding='utf-8') as f:
        yaml.dump({"groups": groups}, f, allow_unicode=True, default_flow_style=False)
