import sys

from PIL import Image, ImageDraw, ImageFont

from utils import config, get_timestamp, get_logger


logger = get_logger(__name__)


def calc_box_margin(base_image, image):
    base_img_width = base_image.size[0]
    base_img_height = base_image.size[1]
    img_width = image.size[0]
    img_height = image.size[1]

    left_margin = int(base_img_width / 2 - img_width / 2)
    top_margin = int(base_img_height / 2 - img_height / 2)

    logger.debug("Left margin: %f | Top margin: %f", left_margin, top_margin)
    return (left_margin, top_margin)


def composite(image):
    img_config = config["final_image"]

    resolution = (img_config["resolution"]["width"], img_config["resolution"]["height"])
    background_color = tuple(img_config["background_color"])

    base_image = Image.new("RGBA", resolution, background_color)

    box_margin = calc_box_margin(base_image, image)
    base_image.paste(image, box_margin, image)

    logger.info("Composited")
    return base_image


def text_overlay(image):
    text_config = config["final_image"]["text_overlay"]

    text_img = Image.new("RGBA", image.size, (255, 255, 255, 0))
    try:
        font = ImageFont.truetype(text_config["font_path"], text_config["font_size"])
    except IOError:
        logger.error("Cannot load font")
        sys.exit()

    ctx = ImageDraw.Draw(text_img)

    font_color = tuple(text_config["font_color"])
    text_position = tuple(text_config["position"])
    text = text_config["text"].replace("[timestamp]", get_timestamp())
    logger.debug('Text content:\n"%s"', text)

    ctx.multiline_text(
        xy=text_position,
        text=text,
        font=font,
        fill=font_color,
        align=text_config["align"],
        spacing=text_config["spacing"],
    )

    logger.info("Overlayed text")
    return Image.alpha_composite(image, text_img)


def resize(image):
    resolution = (
        config["final_image"]["small_resolution"]["width"],
        config["final_image"]["small_resolution"]["height"],
    )
    image.thumbnail(size=resolution, resample=Image.LANCZOS)
    logger.info("Created small image")


def save(image, path):
    try:
        image.save(path)
    except KeyError:
        logger.error("Cannot determine output format from filename")
        sys.exit()
    except IOError:
        logger.error("Cannot write image file")
        sys.exit()


def final_image():
    img_config = config["final_image"]

    try:
        orig_img = Image.open(config["graph_image"]["cache_path"])
    except IOError:
        logger.error("Cannot open image file")
        sys.exit()

    img = composite(orig_img)
    img = text_overlay(img)

    save(img, img_config["save_path"])
    logger.info("Image saved")

    resize(img)
    save(img, img_config["small_save_path"])
    logger.info("Small image saved")
