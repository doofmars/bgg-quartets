import configparser
import os
import shutil
import xml.etree.ElementTree as ET
import requests
from ruamel.yaml import YAML

from PIL import Image, ImageDraw, ImageFont, ImageColor

CONVERSION_IN_MM = 25.4

config = configparser.ConfigParser()


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
            for game in group['games']:
                selected_games.append({'id': game,
                                       'group': group['name'],
                                       'color': group['color']})
    return selected_games


def generate_cards():
    generate_config = config['generate']
    card_selection = get_selection(generate_config['SELECTION'])
    collection = load_data()
    for card_config in card_selection:
        game_id = card_config["id"]
        game = collection.getroot().find(f'item[@objectid="{game_id}"]')
        if game is not None:
            render_as_card(game, card_config, generate_config)
        else:
            print(f'Failed to find game with id {game_id} in collection')
            exit(1)


def fetch_image(id, url):
    image_path = os.path.join(config['fetch']['IMAGE_CACHE_DIRECTORY'], f"{id}.jpeg")
    if os.path.exists(image_path):
        print(f'Image for game {id} is already cached')
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


def render_as_card(game, card_config, gen_config):
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
    fnt = ImageFont.truetype(gen_config['FONT'], dpi(4))

    # Fetch and add image
    image_path = fetch_image(game_id, game.find('image').text)
    game_image = load_sized_image(image_path, dpi(49), dpi(38))

    # get a drawing context
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((cut_border, cut_border, print_width + cut_border, print_height + cut_border),
                        radius=dpi(5), width=1, outline=(200, 200, 200))
    d.rounded_rectangle((cut_border + card_border, cut_border + card_border,
                         print_width + cut_border - card_border, print_height + cut_border - card_border),
                        radius=dpi(3), width=1, fill=ImageColor.getrgb(card_config['color']))

    # draw multiline text
    d.text((dpi(9), dpi(52)), game.find('name').text, font=fnt, fill=(0, 0, 0))

    d.text((dpi(10), dpi(58)), game.find('yearpublished').text, font=fnt, fill=(0, 0, 0))
    d.text((dpi(10), dpi(64)), f"{game.find('stats').get('minplaytime')}-{game.find('stats').get('maxplaytime')}", font=fnt, fill=(0, 0, 0))
    d.text((dpi(10), dpi(70)), game.find('./boardgame/statistics/ratings/average').text, font=fnt, fill=(0, 0, 0))
    d.text((dpi(10), dpi(76)), game.find('./boardgame/statistics/ratings/owned').text, font=fnt, fill=(0, 0, 0))
    d.text((dpi(10), dpi(82)), game.find('./boardgame/statistics/ratings/averageweight').text, font=fnt, fill=(0, 0, 0))

    d.text((dpi(35), dpi(58)), f"{game.find('stats').get('minplayers')}-{game.find('stats').get('maxplayers')}", font=fnt, fill=(0, 0, 0))
    d.text((dpi(35), dpi(64)), game.find('./boardgame/age').text, font=fnt, fill=(0, 0, 0))
    d.text((dpi(35), dpi(70)), game.find('./stats/rating').get('value'), font=fnt, fill=(0, 0, 0))
    d.text((dpi(35), dpi(76)), game.find('numplays').text, font=fnt, fill=(0, 0, 0))
    d.text((dpi(35), dpi(82)), game.find('yearpublished').text, font=fnt, fill=(0, 0, 0))
    card_path = os.path.join(gen_config['CARD_CACHE'], f'{game_id}.png')
    # Add the game image

    # paste image centered
    out.paste(game_image, (int(width/2 - game_image.width / 2), dpi(14)))

    # Save results
    out.save(card_path)
    print(f'Created card for game {game_id} in {card_path}')


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
    return img.resize((int(width * ratio),  int(height * ratio)))


def dpi(length) -> int:
    """
    Get the length in pixeln converted by dpi

    :param length: input length in mm
    :return: pixel appropriation to the given dpi value
    """
    dpi_value = int(config['generate']['DPI'])
    return round(int(length) * (int(dpi_value) / CONVERSION_IN_MM))


if __name__ == '__main__':
    config.read("config.ini")
    generate_cards()
