import configparser
import os
import shutil
import xml.etree.ElementTree as ET
import requests

from PIL import Image, ImageDraw, ImageFont

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


def generate_cards():
    generate_config = config['generate']
    collection = load_data()
    for game in collection.getroot().findall('item'):
        render_as_card(game, generate_config)
        break


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
            exit()


def render_as_card(game, gen_config):
    dpi = int(gen_config['DPI'])
    width = get_length_with_dpi(gen_config['WIDTH'], dpi)
    height = get_length_with_dpi(gen_config['HEIGHT'], dpi)
    cut_border = get_length_with_dpi(gen_config['CUT_BORDER'], dpi)
    card_border = get_length_with_dpi(gen_config['CARD_BORDER'], dpi)
    # create an image
    out = Image.new('RGB', (width + 2 * cut_border, height + 2 * cut_border), color=(255, 255, 255))

    # get a font
    fnt = ImageFont.truetype(gen_config['FONT'], 40)
    # get a drawing context

    # Fetch and add image
    image_path = fetch_image(game.get("objectid"), game.find('image').text)
    game_image = Image.open(image_path).resize((100, 100))

    out.paste(game_image, (100, 170))

    d = ImageDraw.Draw(out)
    d.rounded_rectangle((cut_border, cut_border, width + cut_border, height + cut_border),
                        radius=get_length_with_dpi(5, dpi), width=1, outline=(200, 200, 200))
    d.rounded_rectangle((cut_border + card_border, cut_border + card_border,
                         width + cut_border - card_border, height + cut_border - card_border),
                        radius=get_length_with_dpi(3, dpi), width=1, outline=(200, 200, 200))

    # draw multiline text
    d.text((200, 600), game.find('name').text, font=fnt, fill=(0, 0, 0))

    d.text((120, 680), game.find('yearpublished').text, font=fnt, fill=(0, 0, 0))
    d.text((120, 760), f"{game.find('stats').get('minplaytime')}-{game.find('stats').get('maxplaytime')}", font=fnt, fill=(0, 0, 0))
    d.text((120, 840), game.find('./boardgame/statistics/ratings/average').text, font=fnt, fill=(0, 0, 0))
    d.text((120, 920), game.find('./boardgame/statistics/ratings/owned').text, font=fnt, fill=(0, 0, 0))
    d.text((120, 1000), game.find('./boardgame/statistics/ratings/averageweight').text, font=fnt, fill=(0, 0, 0))

    d.text((450, 680), f"{game.find('stats').get('minplayers')}-{game.find('stats').get('maxplayers')}", font=fnt, fill=(0, 0, 0))
    d.text((450, 760), game.find('./boardgame/age').text, font=fnt, fill=(0, 0, 0))
    d.text((450, 840), game.find('./stats/rating').get('value'), font=fnt, fill=(0, 0, 0))
    d.text((450, 920), game.find('numplays').text, font=fnt, fill=(0, 0, 0))
    d.text((450, 1000), game.find('yearpublished').text, font=fnt, fill=(0, 0, 0))
    out.save('test.png', dpi=(dpi, dpi))
    pass


def get_length_with_dpi(length, dpi) -> int:
    """
    Get the length in pixeln converted by dpi

    :param length: input length in mm
    :param dpi: the file dpi used for conversion
    :return: pixel appropriation to the given dpi value
    """
    return round(int(length) * (int(dpi) / CONVERSION_IN_MM))


if __name__ == '__main__':
    config.read("config.ini")
    generate_cards()
