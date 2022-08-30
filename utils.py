import os
import sys
import json
from datetime import datetime
import shutil
import requests
import time

import logging
from logging import config as log_config

import sqlite3


DUMP_URL = 'https://www.nationstates.net/pages/nations.xml.gz'


log_config.fileConfig('config/logging.ini')


def get_logger(name):
    logger = logging.getLogger(name)

    return logger


logger = get_logger(__name__)

# Class to manage configurations
class Configuration(object):
    def __init__(self):
        self.config = None
        try:
            with open('config/config_tsp.json') as file:
                self.config = json.loads(file.read().replace("\n", ""))
            logger.info('Loaded configuration file')
        except IOError:
            logger.error('Cannot open configuration file')
            sys.exit()
        except ValueError:
            logger.error('Syntax errors in configuration file')
            sys.exit()

        if self.config['first_time_run'] is True:
            logger.info('First time running enabled')

    def __getitem__(self, item):
        return self.config[item]


config = Configuration()


# Get timestamp
def get_timestamp(time_format='%Y/%m/%d %H:%M:%S'):
    if config['data']['false_time'] is False:
        timestamp = str(datetime.utcnow().strftime(time_format))
    else:
        timestamp = config['data']['false_time']

    logger.debug('Got timestamp: %s', timestamp)
    return timestamp


def add_timestamp(text):
    return text.replace('[timestamp]', get_timestamp('%Y/%m/%d'))


# Round number
def round_str(value, disp_format="%.2f", digit=3):
    rounded_str = disp_format % round(value, digit)

    return rounded_str


# Download data dump if one does not exist
def get_datadump():
    file_name = config['data']['dump_file']
    if os.path.isfile(file_name):
        logger.info('Data dump file already exists. No download')
        return

    respond = requests.get(DUMP_URL, headers={'user-agent': config['auth']['user_agent']}, stream=True)

    try:
        respond.raise_for_status()
    except requests.HTTPError as e:
        logger.error('Failed to download data dump. HTTP error: %d',
                     e.response.status_code)
        sys.exit()
    except requests.exceptions.ConnectionError as e:
        logger.error('Failed to download data dump. Connection error',
                     exc_info=True)
        sys.exit()

    with open(file_name, 'wb') as file:
            shutil.copyfileobj(respond.raw, file)
    logger.info('Downloaded data dump')


# Get SQL connection and cursor
def get_sql_interface(path, no_conn=False, backup=False):
    try:
        conn = sqlite3.connect(path)
        logger.info('Got SQL connection')
        cursor = conn.cursor()
        logger.info('Got SQL cursor')
    except sqlite3.DatabaseError:
        logger.error('SQL database error', exc_info=True)
        sys.exit()

    if backup is True:
        filename = "{}.backup".format(path.split('/')[-1])
        backup_filepath = os.path.join(config['db_archive']['backup_path'], filename)

        shutil.copyfile(path, backup_filepath)

        logger.info('Created database backup: "%s"', backup_filepath)

    if no_conn is True:
        return cursor

    return cursor, conn


# Get value from a list of tuple: (nation_name, val)
def get_value_from_list(list, nation):
    return dict(list)[nation]


# Get change in value with percentage from current value and last value
def get_change_with_perc(current_value, last_value):
    change = current_value
    perc_change = None

    if last_value is None or last_value == 0:
        return (change, perc_change)

    change = current_value - last_value
    perc_change = float(change) / float(last_value) * 100

    return (change, perc_change)


# Wrap standard bbcode around a string
def style_text(text, highlight=False):
    styled_text = config['dispatch']['standard_bbcode'].format(text)

    if highlight is True:
        styled_text = config['dispatch']['highlight_bbcode'].format(styled_text)

    return styled_text


def wrap_nation_bbcode(nation_name, noflag=False):
    if noflag:
        return "[nation=noflag]{}[/nation]".format(nation_name)
    else:
        return "[nation]{}[/nation]".format(nation_name)


# Generate a table from list with specificed column number
def gen_list_table(list, column_num, disable_format=False, noflag=False):
    table_bbcode_text = ""

    for i in range(0, len(list), column_num):
        table_bbcode_text += "[tr]"
        try:
            for j in range(i, i + column_num):
                if disable_format:
                    table_bbcode_text += "[td]{}[/td]".format(wrap_nation_bbcode(list[j], noflag))
                else:
                    table_bbcode_text += "[td]{}[/td]".format(style_text(wrap_nation_bbcode(list[j], noflag)))
        except(IndexError):
            pass
        table_bbcode_text += "[/tr]"

    return table_bbcode_text


def gen_change_format(tuple):
    change = tuple[0]

    if isinstance(change, float):
        change = round_str(change)

    if tuple[1] is None:
        perc_change = 'N/A'
    else:
        perc_change = round_str(tuple[1])

    if tuple[0] > 0:
        return "[color=#32CD32]+{} (+{} %)[/color]".format(change, perc_change)
    elif tuple[0] < 0:
        return "[color=#FF0000]{} ({} %)[/color]".format(change, perc_change)
    else:
        return "{} ({} %)".format(change, perc_change)


def get_formatted_census_cell(cell_data, nation_bbcode=False, highlight=False):
    cell = "[td]{}[/td]"

    if nation_bbcode is True:
        cell = cell.format(style_text(wrap_nation_bbcode(cell_data), highlight))
    elif isinstance(cell_data, tuple):
        cell = cell.format(style_text(gen_change_format(cell_data), highlight))
    elif isinstance(cell_data, float):
        cell = cell.format(style_text(round_str(cell_data), highlight))
    else:
        cell = cell.format(style_text(cell_data, highlight))

    return cell


# Generate a census table from a list of lists
def gen_census_table(list, nation_idx, highlight_column_idx=[], highlight_check_idx=0, disp_rank=True):
    table_bbcode_text = ""

    rank = 0
    for i in list:
        table_bbcode_text += "[tr]"

        if disp_rank is True:
            rank += 1
            table_bbcode_text += "[td]{}[/td]".format(style_text(rank))

        for j in i:
            if isinstance(j, bool):
                continue

            if i.index(j) == nation_idx:
                if i.index(j) in highlight_column_idx and i[highlight_check_idx]:
                    cell = get_formatted_census_cell(j, nation_bbcode=True, highlight=True)
                else:
                    cell = get_formatted_census_cell(j, nation_bbcode=True)
            elif i.index(j) in highlight_column_idx and i[highlight_check_idx]:
                cell = get_formatted_census_cell(j, highlight=True)
            else:
                cell = get_formatted_census_cell(j)

            table_bbcode_text += cell

        table_bbcode_text += "[/tr]"

    return table_bbcode_text


# Generate BBcode for a row of centered text
def gen_center_td(text):
    return "[tr][td][center]{}[/center][/td][/tr]".format(style_text(text))


def gen_text_list(list, separator=', ', noflag=False):
    text_list = separator.join([wrap_nation_bbcode(i, noflag) for i in list])

    return text_list

