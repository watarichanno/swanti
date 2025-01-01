import sys

import requests
import pyimgur
import webbrowser

from utils import config, get_logger, add_timestamp
from data import data


logger = get_logger(__name__)


def authenticate(imgur):
    auth_url = imgur.authorization_url("pin")
    logger.debug('Authorization URL: "%s"', auth_url)

    try:
        webbrowser.open(auth_url)
    except webbrowser.Error:
        logger.error("Cannot open browser")

    pin = input("Enter Imgur pin number: ")
    try:
        imgur.exchange_pin(pin)
        logger.info("Authenticated")
    except requests.HTTPError as e:
        logger.error(
            "Failed to authenticate. Error %d", e.response.status_code, exc_info=True
        )
        sys.exit()


def get_imgur():
    imgur_auth_config = config["imgur"]["auth"]
    refresh_token_file = open(imgur_auth_config["refresh_token_path"], "r+")

    imgur = None

    # Get refresh token if one does not exist
    if refresh_token_file.read() == "":
        logger.info("No refresh token found")

        imgur = pyimgur.Imgur(
            imgur_auth_config["client_id"], imgur_auth_config["client_secret"]
        )
        authenticate(imgur)
        refresh_token_file.write(imgur.refresh_token)
        logger.info("Wrote refresh token into file")
        logger.debug('Refresh token: "%s"', imgur.refresh_token)
    else:
        logger.info("Found refresh token")
        refresh_token_file.seek(0)
        refresh_token = refresh_token_file.read()

        imgur = pyimgur.Imgur(
            imgur_auth_config["client_id"],
            imgur_auth_config["client_secret"],
            refresh_token=refresh_token,
        )

        try:
            imgur.refresh_access_token()
            logger.info("Refreshed access token")
        except Exception as e:
            logger.error(e)
            sys.exit()

    return imgur


def upload_image():
    imgur_config = config["imgur"]["image"]
    imgur = get_imgur()

    try:
        img = imgur.upload_image(
            path=config["final_image"]["small_save_path"],
            title=add_timestamp(imgur_config["title"]),
            description=add_timestamp(imgur_config["description"]),
            album=imgur_config["album_id"],
        )
        logger.info("Uploaded image to Imgur")
    except requests.HTTPError as e:
        logger.error(
            "Failed to upload to Imgur. Error: %d",
            e.response.status_code,
            exc_info=True,
        )

    data["endo_map_small_url"] = img.link
