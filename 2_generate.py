import configparser
import os
import xml.etree.ElementTree as ET

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


def render_as_card(game_data, gen_config):
    size = get_size(gen_config)
    # create an image
    out = Image.new('RGB', size, color=(255, 255, 255))

    # get a font
    fnt = ImageFont.truetype(gen_config['FONT'], 40)
    # get a drawing context
    d = ImageDraw.Draw(out)

    # draw multiline text
    d.multiline_text((10, 10), "Hello\nWorld", font=fnt, fill=(0, 0, 0))

    out.show()
    pass


def get_size(gen_config) -> tuple[int, int]:
    """
    Get size as tuple

    :param gen_config: the generation config
    :return: a tuple with rounded image size pixel values
    """
    x = round((int(gen_config['WIDTH']) + 2 * int(gen_config['BORDER'])) * (int(gen_config['DPI']) / CONVERSION_IN_MM))
    y = round((int(gen_config['HEIGHT']) + 2 * int(gen_config['BORDER'])) * (int(gen_config['DPI']) / CONVERSION_IN_MM))
    return x, y


if __name__ == '__main__':
    config.read("config.ini")
    generate_cards()
