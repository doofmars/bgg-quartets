import configparser
import os
import shutil
import threading
import xml.etree.ElementTree as ET
import requests
from ruamel.yaml import YAML

from PIL import Image, ImageDraw, ImageFont, ImageColor

CONVERSION_IN_MM = 25.4

config = configparser.ConfigParser()

ICONS = [
    ('iconmonstr-calendar-4-240.png', 10, 59),
    ('iconmonstr-time-13-240.png', 10, 65),
    ('iconmonstr-star-half-lined-240.png', 10, 71),
    ('iconmonstr-product-14-240.png', 10, 77),
    ('flaticon-problem.png', 10, 83),

    ('iconmonstr-user-29-240.png', 36, 59),
    ('iconmonstr-user-23-240.png', 36, 65),
    ('flaticon-age-group.png', 36, 71),
    ('iconmonstr-thumb-14-240.png', 36, 77),
    ('iconmonstr-video-15-240.png', 36, 83),
]


def load_data():
    """
    Load data cache

    :return: soup to parse
    """
    if not os.path.exists(config['generate']['CARD_CACHE']):
        os.mkdir(config['generate']['CARD_CACHE'])
    if not os.path.exists(config['fetch']['IMAGE_CACHE_DIRECTORY']):
        os.mkdir(config['fetch']['IMAGE_CACHE_DIRECTORY'])
    collection_file_key = config['fetch']['COLLECTION_FILE_KEY']
    collection_file = os.path.join(config['fetch']['RESULT_DIRECTORY'], f'{collection_file_key}.xml')
    if not os.path.exists(collection_file):
        raise FileNotFoundError('Missing collection_file')
    else:
        print(f'Reading {collection_file} from cache')
    return ET.parse(collection_file)


def get_selection(selection_file):
    yaml = YAML(typ='safe')
    selected_games = []
    with open(selection_file, 'r') as fp:
        groups = yaml.load(fp)['groups']
        for group in groups:
            # loop over grops with index
            for index, game in enumerate(group['games']):
                selected_games.append({'id': game,
                                       'index': index,
                                       'group': group['name'],
                                       'category': group['category'],
                                       'top-color': group['top-color'],
                                       'color': group['color']})
    return selected_games


def generate_cards():
    generate_config = config['generate']
    card_selection = get_selection(generate_config['SELECTION'])
    collection = load_data()
    long_names = {}
    for card_config in card_selection:
        game_id = list(card_config["id"].keys())[0]
        game_name = list(card_config["id"].values())[0]

        game = collection.getroot().find(f'item[@objectid="{game_id}"]')
        if game is not None:
            if game_name is None:
                game_name = game.find('name').text
                if len(game_name) > 25:
                    long_names[game_id] = game_name
            threading.Thread(target=render_as_card, args=(game, game_name, card_config, generate_config)).start()
        else:
            print(f'Failed to find game with id {game_id} in collection')
            exit(1)
    if long_names:
        print('Warning, detected long game names:')
        for game_id, game_name in long_names.items():
            print(f'{game_id}: {game_name}')


def fetch_image(id, url):
    image_path = os.path.join(config['fetch']['IMAGE_CACHE_DIRECTORY'], f"{id}.jpeg")
    if os.path.exists(image_path):
        return image_path
    else:
        print('Fetching image from web')
        res = requests.get(url, stream=True)
        if res.status_code == 200:
            with open(image_path, 'wb') as image:
                shutil.copyfileobj(res.raw, image)
            return image_path
        else:
            print(f'Failed to fetch image with id {id} from {url}')
            exit(1)


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


def render_as_card(game, game_name, card_config, gen_config):
    """
    Render a game as a card

    :param game: The game object to render
    :param game_name: The name of the game
    :param card_config: The configuration for the card
    :param gen_config: The card generation configuration
    """
    print_width = dpi(gen_config['WIDTH'])
    print_height = dpi(gen_config['HEIGHT'])
    cut_border = dpi(gen_config['CUT_BORDER'])
    card_border = dpi(gen_config['CARD_BORDER'])
    game_id = game.get('objectid')
    width = print_width + 2 * cut_border
    height = print_height + 2 * cut_border

    # create an image
    out = Image.new('RGB', (width, height), color=(255, 255, 255))

    # get a font
    fnt = ImageFont.truetype(gen_config['FONT_MAIN'], dpi(4))
    fnt_heading = ImageFont.truetype(gen_config['FONT_HEADING'], dpi(4.8))

    # Fetch and add image
    image_path = fetch_image(game_id, game.find('image').text)
    game_image = load_sized_image(image_path, dpi(49), dpi(37))

    # get a drawing context
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((cut_border, cut_border, print_width + cut_border, print_height + cut_border),
                        radius=dpi(5), width=1, outline=(200, 200, 200))
    d.rounded_rectangle((cut_border + card_border, cut_border + card_border,
                         print_width + cut_border - card_border, print_height + cut_border - card_border),
                        radius=dpi(3), width=1, fill=ImageColor.getrgb(card_config['color']))

    # Create backdrop for game name
    d.rounded_rectangle((dpi(9), dpi(52), dpi(56), dpi(57)),
                        radius=dpi(1), fill=ImageColor.getrgb(gen_config['BOX_COLOR']))

    # Create backdrop for game stats
    add_boxes(d, dpi(9), dpi(58), dpi(30), dpi(5), dpi(6), 5, gen_config['BOX_COLOR'])
    add_boxes(d, dpi(35), dpi(58), dpi(56), dpi(5), dpi(6), 5, gen_config['BOX_COLOR'])

    # Create backdrop for header
    d.rounded_rectangle((cut_border + card_border, cut_border + card_border, print_width + cut_border - card_border, dpi(20)),
                        fill=ImageColor.getrgb(card_config['top-color']), radius=dpi(3))
    d.rectangle((cut_border + card_border, dpi(13), print_width + cut_border - card_border, dpi(20)),
                fill=ImageColor.getrgb(card_config['color']))

    # Render header card
    d.text((dpi(9), dpi(7)), f"{card_config['index']}{card_config['group']}", font=fnt_heading, fill=(255, 255, 255))
    _, _, text_width, _ = d.textbbox((0, 0), card_config['category'], font=fnt_heading)
    d.text(((width - text_width) / 2, dpi(7)), card_config['category'], font=fnt_heading, fill=(255, 255, 255))

    # Define default font size for game name
    font_size = 4.8
    fnt_game_name = ImageFont.truetype(gen_config['FONT_HEADING'], dpi(font_size))

    # Calculate the font size to fit the game name box
    _, _, text_width, _ = d.textbbox((0, 0), game_name, font=fnt_game_name)
    # Calculate letter baseline for vertical positioning
    _, _, _, text_height = d.textbbox((0, 0), "A", font=fnt_game_name)
    while text_width > dpi(47.5):
        font_size -= 0.2
        fnt_game_name = ImageFont.truetype(gen_config['FONT_HEADING'], dpi(font_size))
        _, _, text_width, _ = d.textbbox((0, 0), game_name, font=fnt_game_name)
        _, _, _, text_height = d.textbbox((0, 0), "A", font=fnt_game_name)

    # Render game name to canvas
    d.text(((width - text_width) / 2, dpi(55.8) - text_height), game_name, font=fnt_game_name, fill=(0, 0, 0))

    # Draw game stats for the left side
    d.text((dpi(14), dpi(58)), game.find('yearpublished').text, font=fnt, fill=(0, 0, 0))
    playtime = compact_range(game.find('stats').get('minplaytime'), game.find('stats').get('maxplaytime'))
    d.text((dpi(14), dpi(64)), playtime, font=fnt, fill=(0, 0, 0))
    rating = float(game.find('./boardgame/statistics/ratings/average').text)
    d.text((dpi(14), dpi(70)), f'{rating:.2f}', font=fnt, fill=(0, 0, 0))
    games_owned = compact_number(int(game.find('./boardgame/statistics/ratings/owned').text))
    d.text((dpi(14), dpi(76)), games_owned, font=fnt, fill=(0, 0, 0))
    weight = float(game.find('./boardgame/statistics/ratings/averageweight').text)
    d.text((dpi(14), dpi(82)), f'{weight:.2f}', font=fnt, fill=(0, 0, 0))

    # Draw game stats for the right side
    players = compact_range(game.find('stats').get('minplayers'), game.find('stats').get('maxplayers'))
    d.text((dpi(40), dpi(58)), players, font=fnt, fill=(0, 0, 0))
    players_poll_result = compact_poll_result(game.findall('./boardgame/poll[@name="suggested_numplayers"]/results'))
    d.text((dpi(40), dpi(64)), players_poll_result, font=fnt, fill=(0, 0, 0))
    d.text((dpi(40), dpi(70)), f"{game.find('./boardgame/age').text}+", font=fnt, fill=(0, 0, 0))
    user_rating = game.find('./stats/rating').get('value')
    if user_rating != 'N/A':
        d.text((dpi(40), dpi(76)), user_rating, font=fnt, fill=(0, 0, 0))
    user_plays = int(game.find('numplays').text)
    if user_plays > 10:
        d.text((dpi(40), dpi(82)), str(user_plays), font=fnt, fill=(0, 0, 0))
    else:
        add_lines(d, dpi(40), dpi(83), user_plays)

    card_path = os.path.join(gen_config['CARD_CACHE'], f'{card_config["group"]}{card_config["index"]}-{game_id}.png')
    # Add the game image
    out.paste(game_image, (int(width / 2 - game_image.width / 2), dpi(14)))

    # load image with transparency
    for icon in ICONS:
        add_icon(out, icon[0], icon[1], icon[2])

    # Save results
    out.save(card_path)
    print(f'Created card for game {game_id} in {card_path}')


def add_icon(out, icon_name, position_x, position_y):
    """
    Add an icon to the card

    :param out: The image to add the icon to
    :param icon_name: The name of the icon to add
    :param position_x: The x position of the icon
    :param position_y: The y position of the icon
    """
    icon = load_sized_image(os.path.join('resources', icon_name), dpi(3), dpi(3))
    out.paste(icon, (dpi(position_x), dpi(position_y)), icon)


def add_boxes(canvas, start_left, start_top, end_right, box_height, step, box_count, color):
    """
    Add boxes to the canvas

    :param canvas: The canvas to add the boxes to
    :param start_left: The left position of the first box
    :param start_top: The top position of the first box
    :param end_right: The right position of the last box
    :param box_height: The height of the boxes
    :param step: The step between the boxes
    :param box_count: The number of boxes to add
    :param color: The color of the boxes
    """
    for i in range(0, box_count):
        canvas.rounded_rectangle((start_left, start_top, end_right, start_top + box_height),
                                 radius=dpi(1), fill=ImageColor.getrgb(color))
        start_top += step


def add_lines(canvas, x, y, number_of_lines):
    """
    Add counting lines to the canvas

    :param canvas: the canvas to add the lines to
    :param x: starting x position
    :param y: starting y position
    :param number_of_lines: the number of lines to add
    """
    for i in range(0, number_of_lines):
        if (i+1) % 5 == 0:
            canvas.line((x, y, x - dpi(3), y + dpi(3)), fill=(0, 0, 0), width=dpi(0.2))
            x += dpi(0.8)
        else:
            canvas.line((x, y, x, y + dpi(3)), fill=(0, 0, 0), width=dpi(0.2))
            x += dpi(0.6)


def load_sized_image(image_path, max_width, max_height):
    """
    Load an image from path and resize maintaining the aspect ratio

    :param image_path: path to image
    :param max_width: the maximum width after resize
    :param max_height: the maximum height after resize
    """
    img = Image.open(image_path)
    width, height = img.size
    ratio = min(max_width / width, max_height / height)
    return img.resize((int(width * ratio), int(height * ratio)))


def dpi(length) -> int:
    """
    Get the length in pixeln converted by dpi

    :param length: input length in mm
    :return: pixel appropriation to the given dpi value
    """
    dpi_value = int(config['generate']['DPI'])
    return int(float(length) * (dpi_value / CONVERSION_IN_MM))


if __name__ == '__main__':
    config.read("config.ini")
    generate_cards()
