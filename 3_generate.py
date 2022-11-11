import os
import shutil
import threading

import requests
from PIL import Image, ImageDraw, ImageFont, ImageColor
from ruamel import yaml

CONVERSION_IN_MM = 25.4

config = yaml.safe_load(open('config.yaml', 'r', encoding='utf-8'))

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


def get_selection(selection_file):
    selected_games = []
    with open(selection_file, 'r', encoding='utf-8') as fp:
        groups = yaml.safe_load(fp)['groups']
        # iterate over key and value of dict groups
        for group_name, group_data in groups.items():
            # loop over games dictionary with index
            for index, game in enumerate(group_data['games']):
                game['index'] = index
                game['group'] = group_name
                game['category'] = group_data['category']
                game['color'] = group_data['color']
                game['top-color'] = group_data['top-color']
                selected_games.append(game)
    return selected_games


def generate_cards():
    if not os.path.exists(config['generate']['cards_directory']):
        os.mkdir(config['generate']['cards_directory'])
    image_cache_path = os.path.join(config['general']['cache_directory'], config['general']['image_cache_directory'])
    if not os.path.exists(image_cache_path):
        os.mkdir(image_cache_path)

    generate_config = config['generate']
    selection_file_path = os.path.join(config['general']['cache_directory'], config['general']['selection_file_key'])
    card_selection = get_selection(selection_file_path)
    for card_data in card_selection:
        threading.Thread(target=render_as_card, args=(card_data, generate_config)).start()
    render_card_back(generate_config)


def fetch_image(game_id, url):
    image_path = os.path.join(
        config['general']['cache_directory'],
        config['general']['image_cache_directory'],
        f"{game_id}.jpg")
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


def render_as_card(card_data, gen_config):
    """
    Render a game as a card

    :param card_data: The data of the game
    :param gen_config: The card generation configuration
    """
    print_width = dpi(gen_config['width'])
    print_height = dpi(gen_config['height'])
    cut_border = dpi(gen_config['cut_border'])
    card_border = dpi(gen_config['card_border'])
    width = print_width + 2 * cut_border
    height = print_height + 2 * cut_border

    # create an image
    out = Image.new('RGB', (width, height), color=(255, 255, 255))

    # get a font
    fnt = ImageFont.truetype(gen_config['font_main'], dpi(4))
    fnt_heading = ImageFont.truetype(gen_config['font_heading'], dpi(4.8))

    # Fetch and add image
    image_path = fetch_image(card_data['_id'], card_data['image'])
    game_image = load_sized_image(image_path, dpi(49), dpi(37))

    # get a drawing context
    d = ImageDraw.Draw(out)
    if gen_config['print_cut_border']:
        d.rounded_rectangle((cut_border, cut_border, print_width + cut_border, print_height + cut_border),
                            radius=dpi(5), width=1, outline=(200, 200, 200))
    d.rounded_rectangle((cut_border + card_border, cut_border + card_border,
                         print_width + cut_border - card_border, print_height + cut_border - card_border),
                        radius=dpi(3), width=1, fill=ImageColor.getrgb(card_data['color']))

    # Create backdrop for game name
    d.rounded_rectangle((dpi(9), dpi(52), dpi(56), dpi(57)),
                        radius=dpi(1), fill=ImageColor.getrgb(gen_config['box_color']))

    # Create backdrop for game stats
    add_boxes(d, dpi(9), dpi(58), dpi(30), dpi(5), dpi(6), 5, gen_config['box_color'])
    add_boxes(d, dpi(35), dpi(58), dpi(56), dpi(5), dpi(6), 5, gen_config['box_color'])

    # Create backdrop for header
    d.rounded_rectangle(
        (cut_border + card_border, cut_border + card_border, print_width + cut_border - card_border, dpi(20)),
        fill=ImageColor.getrgb(card_data['top-color']), radius=dpi(3))
    d.rectangle((cut_border + card_border, dpi(13), print_width + cut_border - card_border, dpi(20)),
                fill=ImageColor.getrgb(card_data['color']))

    # Render header card
    d.text((dpi(8), dpi(7)), f"{card_data['index']}{card_data['group']}", font=fnt_heading, fill=(255, 255, 255))
    _, _, text_width, _ = d.textbbox((0, 0), card_data['category'], font=fnt_heading)
    d.text(((width - text_width) / 2, dpi(7)), card_data['category'], font=fnt_heading, fill=(255, 255, 255))

    # Define default font size for game name
    font_size = 4.8
    fnt_game_name = ImageFont.truetype(gen_config['font_heading'], dpi(font_size))

    # Calculate the font size to fit the game name box
    _, _, text_width, _ = d.textbbox((0, 0), card_data['name'], font=fnt_game_name)
    # Calculate letter baseline for vertical positioning
    _, _, _, text_height = d.textbbox((0, 0), "A", font=fnt_game_name)
    while text_width > dpi(47.5):
        font_size -= 0.2
        fnt_game_name = ImageFont.truetype(gen_config['font_heading'], dpi(font_size))
        _, _, text_width, _ = d.textbbox((0, 0), card_data['name'], font=fnt_game_name)
        _, _, _, text_height = d.textbbox((0, 0), "A", font=fnt_game_name)

    # Render game name to canvas
    d.text(((width - text_width) / 2, dpi(55.8) - text_height), card_data['name'], font=fnt_game_name, fill=(0, 0, 0))

    # Draw game stats for the left side
    d.text((dpi(14), dpi(58)), card_data['year'], font=fnt, fill=(0, 0, 0))
    d.text((dpi(14), dpi(64)), card_data['playtime'], font=fnt, fill=(0, 0, 0))
    d.text((dpi(14), dpi(70)), card_data['rating'], font=fnt, fill=(0, 0, 0))
    d.text((dpi(14), dpi(76)), card_data['owners'], font=fnt, fill=(0, 0, 0))
    d.text((dpi(14), dpi(82)), card_data['weight'], font=fnt, fill=(0, 0, 0))

    # Draw game stats for the right side
    d.text((dpi(40), dpi(58)), card_data['players'], font=fnt, fill=(0, 0, 0))
    d.text((dpi(40), dpi(64)), card_data['players_recommended'], font=fnt, fill=(0, 0, 0))
    d.text((dpi(40), dpi(70)), card_data['age'], font=fnt, fill=(0, 0, 0))
    if card_data['user_rating'] != 'N/A':
        d.text((dpi(40), dpi(76)), card_data['user_rating'], font=fnt, fill=(0, 0, 0))
    if card_data['user_play_count'] > 10:
        d.text((dpi(40), dpi(82)), str(card_data['user_play_count']), font=fnt, fill=(0, 0, 0))
    else:
        add_lines(d, dpi(40), dpi(83), card_data['user_play_count'])

    card_file_name = f'{card_data["group"]}{card_data["index"]}-{card_data["_id"]}.png'
    card_path = os.path.join(gen_config['cards_directory'], card_file_name)
    # Add the game image
    out.paste(game_image, (int(width / 2 - game_image.width / 2), dpi(14)))

    # load image with transparency
    for icon in ICONS:
        add_icon(out, icon[0], icon[1], icon[2])

    # Save results
    out.save(card_path)
    print(f'Created card for game {card_data["_id"]} in {card_path}')


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
        if (i + 1) % 5 == 0:
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


def render_card_back(gen_config):
    """
    Render the card back

    :param gen_config: The configuration for the card back
    """
    print_width = dpi(gen_config['width'])
    print_height = dpi(gen_config['height'])
    cut_border = dpi(gen_config['cut_border'])
    card_border = dpi(gen_config['card_border'])
    width = print_width + 2 * cut_border
    height = print_height + 2 * cut_border

    card_back = Image.new('RGB', (width, height), color=(255, 255, 255))

    # get a drawing context
    if gen_config['print_cut_border']:
        d = ImageDraw.Draw(card_back)
        d.rounded_rectangle((cut_border, cut_border, print_width + cut_border, print_height + cut_border),
                            radius=dpi(5), width=1, outline=(200, 200, 200))

    back_image = Image.open(gen_config['card_back_image']).resize(card_back.size)
    mask = Image.new("L", card_back.size, 255)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((cut_border + card_border, cut_border + card_border,
                            print_width + cut_border - card_border, print_height + cut_border - card_border),
                           radius=dpi(3), width=1, fill=0)
    card_back = Image.composite(card_back, back_image, mask)

    # Safe back image to file
    card_back_path = os.path.join(gen_config['cards_directory'], gen_config['card_back_file_name'])
    card_back.save(card_back_path)
    print(f'Created card back in {card_back_path}')


def dpi(length) -> int:
    """
    Get the length in pixeln converted by dpi

    :param length: input length in mm
    :return: pixel appropriation to the given dpi value
    """
    dpi_value = int(config['generate']['dpi'])
    return int(float(length) * (dpi_value / CONVERSION_IN_MM))


if __name__ == '__main__':
    generate_cards()
