import sys

import requests
from html.parser import HTMLParser

from utils import get_logger
from utils import config


PING_API_URL = "https://www.nationstates.net/cgi-bin/api.cgi?nation={}&q=ping"


logger = get_logger(__name__)


class NSSiteInteraction(object):
    def __init__(self, url, user_agent, nation_name, password):
        self.nationName = nation_name.replace(" ", "_")
        self.password = password
        self.url = url

        user_agent_str = "This script is used by: " + user_agent
        self.headers = {'user-agent': user_agent_str}

        self.cookies = self.set_pin()
        self.id = self.set_id()

    def set_pin(self):
        url = PING_API_URL.format(self.nationName)

        headers = {'X-Password': self.password}
        # Add user agent to header
        headers.update(self.headers)

        respond = requests.get(url, headers=headers)
        try:
            respond.raise_for_status()
        except requests.HTTPError as e:
            logger.error('Failed to get PIN. HTML error: {}'.format(
                         e.response.status_code))
            sys.exit()
        except requests.exceptions.ConnectionError:
            logger.error('Failed to get PIN. Connection error',
                         exc_info=True)
            sys.exit()

        x_pin = respond.headers["X-Pin"]

        logger.info('Got pin')
        logger.debug('Pin: {}\nContent: {}'.format(
                     x_pin, respond.text))

        return dict(pin=x_pin)

    def set_id(self):
        respond = requests.get(self.url,
                               headers=self.headers,
                               cookies=self.cookies)
        try:
            respond.raise_for_status()
        except requests.HTTPError as e:
            logger.error('Failed to get ID. HTML error: {}'.format(
                         e.response.status_code))
            sys.exit()
        except requests.exceptions.ConnectionError as e:
            logger.error('Failed to get ID. Connection error',
                         exc_info=True)
            sys.exit()

        parser = HTMLIdParser()
        parser.feed(respond.text)

        id_num = parser.get_id()

        logger.info('Got ID')
        logger.debug('ID: {}\nContent: {}'.format(
                     id_num, respond.text))
        return id_num

    def execute(self, action, params):
        # Add localid or chk to POST parameters
        params[self.id['type']] = self.id['value']
        # create POST request's destination URL
        url = "https://www.nationstates.net/page={}".format(action)

        respond = requests.post(url,
                                headers=self.headers,
                                data=params,
                                cookies=self.cookies)
        try:
            respond.raise_for_status()

            logger.info('Sent request')
            logger.debug('Response:\n%s', respond.text)
        except requests.HTTPError as e:
            logger.error('Cannot upload dispatch. HTML error: {}'.format(
                         e.response.status_code))
            sys.exit()
        except requests.exceptions.ConnectionError as e:
            logger.error('Cannot upload dispatch. Connection error',
                         exc_info=True)
            sys.exit()


# Parse HTML to find localid or chk
class HTMLIdParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.id = {}

    def handle_starttag(self, tag, attrs):
        if tag == "input" and attrs[1][1] == "localid":
            self.id['type'] = "localid"
            self.id['value'] = attrs[2][1]
        elif tag == "input" and attrs[1][1] == "chk":
            self.id['type'] = "chk"
            self.id['value'] = attrs[2][1]

    def get_id(self):
        return self.id

# Create an instance of NS Interaction Interface
def create_nsii_instance():
    url = "https://www.nationstates.net/page=create_dispatch"
    ns = NSSiteInteraction(url,
                           config['auth']['user_agent'],
                           config['auth']['nation'],
                           config['auth']['password'])

    return ns

