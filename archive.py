import operator

import networkx as nx
import sqlite3

import utils
from utils import config, get_timestamp, get_sql_interface, get_logger
from utils import get_value_from_list, get_change_with_perc
from data import data


logger = get_logger(__name__)


# Get the name of the last table
def get_last_table(cursor):
    tables = cursor.execute("""SELECT name FROM sqlite_master
                            WHERE type='table'""").fetchall()
    last_table_name = tables[len(tables) - 2][0]

    logger.debug('Got last table name: "%s"', last_table_name)
    return last_table_name


# Get the data of the last table
def get_last_table_data(cursor, nation, column):
    if config['start_month'] is True:
        logger.debug(('Last table data of "%s", column "%s"'
                      'does not exist due to first time run'),
                     nation, column)
        return None

    last_table = get_last_table(cursor)
    params = {'nation': nation}

    query_str = """SELECT {} FROM '{}'
                WHERE nation = :nation""".format(column, last_table)

    last_data = cursor.execute(query_str, params).fetchone()

    logger.debug('Got last table data of "%s", column "%s": %r',
                 nation, column, last_data)
    return last_data


# Get the data for the last row of a table
def get_data_last_row(cursor, table, column):
    if config['first_time_run'] is True:
        logger.debug(('Last data of table "%s", column "%s"'
                      'does not exist due to first time run'),
                     table, column)
        return None

    query_str = 'SELECT {} FROM "{}"'.format(column, table)
    results = cursor.execute(query_str).fetchall()
    last_data = results[len(results) - 2]

    logger.debug('Got last data of table "%s", column "%s": %r',
                 table, column, last_data)
    return last_data


# Get data from a table for a nation
def get_data_from_table(cursor, table, nation, column):
    params = {'nation': nation}

    query_str = """SELECT {} FROM '{}'
                WHERE nation = :nation""".format(column, table)
    result = cursor.execute(query_str, params).fetchone()

    logger.debug(('Got data from table "%s", column "%s"'
                  'of nation "%s": %r'),
                 table, column, nation, result)
    return result


def get_last_endo_data(cursor, nation):
    # Get last given endo
    last_given_endo = get_data_from_table(cursor,
                                          'accu',
                                          nation,
                                          "given_endo")[0]
    logger.debug('Got last given endo of "%s": %r',
                 nation, last_given_endo)

    # Get last out endo
    last_out_endo_list = get_last_table_data(cursor, nation, 'out_endo_list')
    logger.debug('Got last out endo of "%s": %r',
                 nation, last_out_endo_list)

    if last_out_endo_list is None:
        return None, last_given_endo

    last_out_endo_set = set(last_out_endo_list[0].split(','))

    return last_out_endo_set, last_given_endo


def get_total_given_endo(cursor, nx_graph, nation):
    current_out_endo_set = set(data['out_endo_dict'][nation])
    last_out_endo_set, last_given_endo = get_last_endo_data(cursor, nation)

    if last_out_endo_set is None:
        given_endo = last_given_endo + nx_graph.out_degree(nation)
    else:
        new_out_endos = current_out_endo_set - last_out_endo_set
        if new_out_endos is not None:
            given_endo = last_given_endo + len(new_out_endos)
        else:
            given_endo = None

    logger.debug('Got total given endo of "%s": %r', nation, given_endo)
    return given_endo


# Get total value to update a column of accu table
def get_total_value(cursor, nation, column, key):
    value = get_value_from_list(data[key], nation)
    last_total_value = get_data_from_table(cursor, 'accu',
                                     nation, column)[0]

    total_value = last_total_value + value

    logger.debug('Got total value "%s" of "%s": %r',
                 key, nation, total_value)
    return total_value


# Check if a nation exists in a table
def check_if_exist(cursor, table, nation):
    params = {'nation': nation}
    query_str = """SELECT nation FROM {}
                WHERE nation=:nation""".format(table)
    result = cursor.execute(query_str, params).fetchone()

    if result is None:
        return False
    else:
        return True


# Add a new nation to accu table if not exist
def add_new_nation(cursor, nation):
    params = {'nation': nation}

    is_exist = check_if_exist(cursor, 'accu',
                              params['nation'])
    if is_exist is False:
        query_str_2 = """INSERT INTO "accu"
                      VALUES (:nation, 0, 0, 0)"""
        cursor.execute(query_str_2, params)
        logger.debug('Inserted new nation "%s" to accu table',
                     params['nation'])


def update_accu_table(cursor, nx_graph, nation):
    add_new_nation(cursor, nation)

    # Everyone starts at zero
    if config['start_month'] is True:
        return

    total_given_endo = get_total_given_endo(cursor, nx_graph, nation)
    total_gained_influence = get_total_value(cursor, nation,
                                             'gained_influence',
                                             'gained_influence_dict')
    total_generated_influence = get_total_value(cursor, nation,
                                                'generated_influence',
                                                'generated_influence_dict')


    params = {'nation': nation,
              'gained_influence': total_gained_influence,
              'generated_influence': total_generated_influence}
    query_str = """UPDATE "accu" SET
                gained_influence=:gained_influence,
                generated_influence=:generated_influence
                WHERE nation=:nation"""

    if total_given_endo is not None:
        params['given_endo'] = total_given_endo
        query_str = """UPDATE "accu" SET
                    given_endo=:given_endo,
                    gained_influence=:gained_influence,
                    generated_influence=:generated_influence
                    WHERE nation=:nation"""

    cursor.execute(query_str, params)
    logger.debug('Updated accu of "%s"', nation)


def update_endo_competition_table(cursor, nx_graph, nation):

    if config['endo_competition'] is False:
        return

    total_given_endo = get_total_given_endo(cursor, nx_graph, nation)


def update_in_out_endo_table(cursor, gen_time, nx_graph, nation):
    params = {'nation': nation, 'out_endo': nx_graph.out_degree(nation),
              'in_endo': nx_graph.in_degree(nation),
              'out_endo_list': ",".join(data['out_endo_dict'][nation])}

    query_str = """INSERT INTO "{}" VALUES
                (:nation, :out_endo,
                :in_endo, :out_endo_list)""".format(gen_time)
    cursor.execute(query_str, params)
    logger.debug('Updated in and out endo of "%s"', nation)


# Add a nation that endorses CRS+delegate if not exist
def update_crsdel_table(cursor, nation):
    params = {'nation': nation}

    is_exist = check_if_exist(cursor, 'crsdel', nation)
    if is_exist is False:
        query_str = "INSERT INTO crsdel VALUES (:nation)"
        cursor.execute(query_str, params)
        logger.debug('Inserted nation "%s" into CRS+Del table', nation)


def update_award_db(cursor, gen_time):
    nx_graph = data.nx_graph
    for nation in nx_graph.nodes:
        update_in_out_endo_table(cursor, gen_time, nx_graph, nation)
        update_accu_table(cursor, nx_graph, nation)

    for nation in data['crsdel_list']:
        update_crsdel_table(cursor, nation)


def update_stats_db(cursor):
    params = {'time': get_timestamp('%Y/%m/%d'),

              'wa_nation_num': data['wa_nation_num'],
              'perc_wa_regional_nation_num': data['perc_wa_to_region'],
              'perc_wa_ns_wa': data['perc_wa_to_ns_wa'],

              'regional_nation_num': data['regional_nation_num'],
              'perc_regional_nation_num_ns': data['perc_regional_nation_num_ns'],
              'ns_nation_num': data['ns_nation_num'],

              'perc_max_in_endo_num_wa': data['perc_max_in_endo_num_wa'],

              'SPCG_avg_in_endo_num': data['SPCG_avg_in_endo_num'],

              'crsdel_num': data['crsdel_num'],
              'perc_crsdel_num_wa': data['perc_crsdel_num_wa'],

              'endo_num': data['endo_num'],
              'density_num': data['density_num'],

              'wa_nations': ",".join(data.nx_graph.nodes)}

    query_str = """INSERT INTO stats VALUES
                (:time,
                 :wa_nation_num, :perc_wa_regional_nation_num, :perc_wa_ns_wa,
                 :regional_nation_num, :perc_regional_nation_num_ns, :ns_nation_num,
                 :perc_max_in_endo_num_wa,
                 :SPCG_avg_in_endo_num,
                 :crsdel_num, :perc_crsdel_num_wa,
                 :endo_num, :density_num,
                 :wa_nations)"""

    cursor.execute(query_str, params)
    logger.info('Updated stats table')


def create_table_index(cursor, name, index, idx_columns):
    if index is not None:
        index_query_str = """CREATE UNIQUE INDEX IF NOT EXISTS '{}' ON '{}'
                          ({})""".format(index, name, idx_columns)
        cursor.execute(index_query_str)
        logger.debug('Created table index "%s" on table "%s", columns "%s"',
                     index, name, idx_columns)


def create_table(cursor, name, columns, unique=False, index=None, idx_columns=None):
    if unique is True:
        query_str = """CREATE TABLE IF NOT EXISTS "{}" ({})""".format(name, columns)
        cursor.execute(query_str)
        create_table_index(cursor, name, index, idx_columns)

        logger.info('Created unique table "%s"', name)
        logger.debug('Created unique table "%s" with columns "%s"', name, columns)

    else:
        query_str = """CREATE TABLE "{}" ({})""".format(name, columns)
        cursor.execute(query_str)
        create_table_index(cursor, name, index, idx_columns)

        logger.info('Created table "%s"', name)
        logger.debug('Created table "%s" with columns "%s"', name, columns)


def create_unique_tables(cursor):
    # This table is used to contain nations that were in WA
    # and number of endorsements given, gained, and generated influence
    create_table(cursor, 'accu',
                ('nation text, given_endo integer,'
                 'gained_influence integer, generated_influence integer'),
                 unique=True, index='accu_table_nation_idx', idx_columns='nation')

    # This table is used to contain nations that endorsed
    # the delegate and CRS
    create_table(cursor, 'crsdel', 'nation text', unique=True)


def create_today_award_table(cursor):
    gen_time = get_timestamp('%Y/%m/%d')

    create_unique_tables(cursor)
    create_table(cursor, gen_time,
                ('nation text, out_endo integer,'
                 'in_endo integer, out_endo_list text'),
                 index='{}_nation_idx'.format(gen_time), idx_columns='nation', unique=True)

    logger.info('Today award table created')
    return gen_time


def create_stats_table(cursor):
    create_table(cursor, 'stats',
                 ('time text,'
                 'wa_nation_num integer, perc_wa_regional_nation_num real, perc_wa_ns_wa real,'
                 'regional_nation_num integer, perc_regional_nation_num_ns real, ns_nation_num integer,'
                 'perc_max_in_endo_num_wa real,'
                 'SPCG_avg_in_endo_num real,'
                 'crsdel_num integer, perc_crsdel_num_wa real,'
                 'endo_num integer, density_num real, wa_nations text'),
                 unique=True)


def save_to_archive():
    archive_config = config['db_archive']
    award_cursor, award_conn = get_sql_interface(archive_config['award_db_path'], backup=True)
    stats_cursor, stats_conn = get_sql_interface(archive_config['stats_db_path'], backup=True)

    award_db_gen_time = create_today_award_table(award_cursor)
    update_award_db(award_cursor, award_db_gen_time)

    create_stats_table(stats_cursor)
    update_stats_db(stats_cursor)

    award_conn.commit()
    stats_conn.commit()
    logger.info('Committed changes')


# ===================Everything above is to write into the archive=======================

# ======================Everything below is to read the archive==========================


# Get average value over many tables
def get_average(cursor, nation, column, tables):
    sum = 0
    count = 0
    for table in tables:
        query_str = "SELECT {} FROM '{}' WHERE nation=:nation".format(
                    column, table[0])
        params = {"nation": nation}
        result = cursor.execute(query_str, params).fetchone()
        if result is not None:
            sum += result[0]
            count += 1

    return sum / count


def get_in_out_endo_rank(cursor, nations, tables):
    avg_in_endos = {}
    avg_out_endos = {}

    for nation in nations:
        if nation in config['data']['excluded'] or nation not in data['wa_nations']:
            continue
        avg_in_endos[nation] = get_average(cursor, nation,
                                          'in_endo', tables)
        avg_out_endos[nation] = get_average(cursor, nation,
                                           'out_endo', tables)

    in_endo_rank = [i[0] for i in sorted(avg_in_endos.items(),
                                         key=operator.itemgetter(1),
                                         reverse=True)]
    out_endo_rank = [i[0] for i in sorted(avg_out_endos.items(),
                                          key=operator.itemgetter(1),
                                          reverse=True)]

    return in_endo_rank, out_endo_rank


def get_rank_of_unique_tables(cursor):
    query_str = """SELECT nation, given_endo FROM accu WHERE given_endo > 20 ORDER BY given_endo DESC"""
    results = cursor.execute(query_str).fetchall()

    given_endo_rank = [i[0] for i in results
                        if i[0] not in config['data']['excluded']
                        and i[0] in data['wa_nations']]

    query_str = "SELECT nation FROM crsdel"
    results = cursor.execute(query_str).fetchall()

    crsdel_endorsers = [i[0] for i in results
                        if i[0] not in config['data']['excluded']
                        and i[0] in data['wa_nations']]

    return given_endo_rank, crsdel_endorsers


def gen_awards(cursor):
    given_endo_rank, crsdel_endorsers = get_rank_of_unique_tables(cursor)

    # Every nation that has been in WA is on the given endo rank
    # list. This is to increase code readability and provide
    # isolation
    nations = given_endo_rank

    # Get a list of in and out endo tables
    tables = cursor.execute("""SELECT name FROM sqlite_master WHERE type='table' AND
                            name NOT IN ('accu', 'crsdel', 'stats')""").fetchall()
    in_endo_rank, out_endo_rank = get_in_out_endo_rank(cursor, nations, tables)

    data['award_given_endo_rank'] = given_endo_rank
    data['award_in_endo_rank'] = in_endo_rank
    data['award_out_endo_rank'] = out_endo_rank
    data['award_crsdel'] = crsdel_endorsers
    data['award_wa_nations'] = nations


def get_census_change(cursor, nation, column, key):
    if config['start_month'] is True:
        return (0, None)

    current_value = get_value_from_list(data[key], nation)
    last_result = get_last_table_data(cursor, nation, column)

    if last_result is None:
        return get_change_with_perc(current_value, None)

    return get_change_with_perc(current_value, last_result[0])


def get_in_endo_census(cursor):
    census = []

    for i in data['in_endo_sorted_list']:
        nation = i[0]
        in_endo_num = i[1]
        change = get_census_change(cursor, nation,
                                   'in_endo', 'in_endo_sorted_list')
        gained_influence = get_data_from_table(cursor, 'accu',
                                               nation, 'gained_influence')[0]


        is_cap_exceed = True

        if nation in config['data']['excluded']:
            is_cap_exceed = False
        elif nation in config['data']['SPCG'] and in_endo_num <= data['SPCG_endo_cap']:
            is_cap_exceed = False
        elif in_endo_num <= data['endo_cap']:
            is_cap_exceed = False

        census.append([nation, in_endo_num, change, gained_influence, is_cap_exceed])

    logger.info('Created in-endo census')
    logger.debug('Content:\n%r:', census)
    return census


def get_out_endo_census(cursor):
    census = []

    for i in data['out_endo_sorted_list']:
        nation = i[0]
        out_endo_num = i[1]

        change = get_census_change(cursor, nation,
                                   'out_endo', 'out_endo_sorted_list')
        perc_wa_nation = float(out_endo_num) / float(data['wa_nation_num'] - 1) * 100
        generated_influence = get_data_from_table(cursor, 'accu',
                                                  nation, 'generated_influence')[0]

        census.append([nation, out_endo_num, change, perc_wa_nation, generated_influence])

    logger.info('Created out-endo census')
    logger.debug('Content:\n%r:', census)
    return census


def get_endotarting_census(cursor):
    census = []

    query_str = """SELECT nation, given_endo FROM accu
                WHERE given_endo > 0 ORDER BY given_endo DESC"""
    if config['endo_competition'] is True:
        query_str = """SELECT nation, given_endo, begin_endo FROM accu
                    WHERE given_endo > 0 ORDER BY given_endo DESC"""
    results = cursor.execute(query_str).fetchall()

    for i in results:
        nation = i[0]
        given_endo = i[1]

        if config['endo_competition'] is True:
            endo_improv = (given_endo - i[2]) / i[2] * 100
            census.append([nation, given_endo, endo_improv])
        else:
            census.append([nation, given_endo])

    logger.info('Created endotarting census')
    logger.debug('Content:\n%r:', census)
    return census


def get_SPCG_census(cursor):
    census = []

    for i in data['SPCG_in_endo_sorted_list']:
        nation = i[0]
        in_endo_num = i[1]
        change = get_census_change(cursor, nation,
                                   'in_endo', 'in_endo_sorted_list')
        census.append([nation, in_endo_num, change])

    logger.info('Created SPCG census')
    logger.debug('Content:\n%r:', census)
    return census


def get_new_wa_nations(cursor):
    if config['first_time_run'] is True:
        return ['N/A']

    current_wa_nation_set = set(data.nx_graph)
    last_wa_nation_set = set(get_data_last_row(cursor, 'stats', 'wa_nations')[0].split(','))

    new_wa_nations = list(current_wa_nation_set - last_wa_nation_set)

    logger.debug('Got new WA nations: %r', new_wa_nations)
    return new_wa_nations


def get_change_from_stats(cursor, column, key):
    change = (0, None)

    if config['first_time_run'] is True:
        logger.debug('Got stats change on first time run of "%s": %r', column, change)
        return change

    last_result = get_data_last_row(cursor, 'stats', column)
    current_value = data[key]

    if last_result is None:
        change = get_change_with_perc(current_value, None)
    else:
        change = get_change_with_perc(current_value, last_result[0])

    logger.debug('Got stats change of "%s": %r', column, change)
    return change


def read_from_archive():
    archive_config = config['db_archive']

    cursor = get_sql_interface(archive_config['award_db_path'], no_conn=True)
    stats_cursor = get_sql_interface(archive_config['stats_db_path'], no_conn=True)

    data['endotarting_census'] = get_endotarting_census(cursor)
    data['out_endo_census'] = get_out_endo_census(cursor)
    data['in_endo_census'] = get_in_endo_census(cursor)
    data['SPCG_census'] = get_SPCG_census(cursor)

    data['new_wa_nations'] = get_new_wa_nations(stats_cursor)

    data['wa_nation_num_change'] = get_change_from_stats(stats_cursor,
                                                         'wa_nation_num',
                                                         'wa_nation_num')
    data['perc_wa_regional_nation_num_change'] = get_change_from_stats(stats_cursor,
                                                 'perc_wa_regional_nation_num',
                                                 'perc_wa_to_region')
    data['perc_wa_ns_wa_change'] = get_change_from_stats(stats_cursor,
                                                         'perc_wa_ns_wa',
                                                         'perc_wa_to_ns_wa')

    data['regional_nation_num_change'] = get_change_from_stats(stats_cursor,
                                                               'regional_nation_num',
                                                               'regional_nation_num')
    data['perc_regional_nation_num_ns_change'] = get_change_from_stats(stats_cursor,
                                                                'perc_regional_nation_num_ns',
                                                                'perc_regional_nation_num_ns')

    data['max_in_endo_num_change'] = data['in_endo_census'][0][2]
    data['perc_max_in_endo_num_wa_change'] = get_change_from_stats(stats_cursor,
                                                               'perc_max_in_endo_num_wa',
                                                               'perc_max_in_endo_num_wa')

    data['SPCG_avg_in_endo_num_change'] = get_change_from_stats(stats_cursor,
                                                                'SPCG_avg_in_endo_num',
                                                                'SPCG_avg_in_endo_num')

    data['crsdel_num_change'] = get_change_from_stats(stats_cursor,
                                                      'crsdel_num',
                                                      'crsdel_num')
    data['perc_crsdel_num_wa_change'] = get_change_from_stats(stats_cursor,
                                                              'perc_crsdel_num_wa',
                                                              'perc_crsdel_num_wa')

    data['endo_num_change'] = get_change_from_stats(stats_cursor,
                                                    'endo_num',
                                                    'endo_num')
    data['density_num_change'] = get_change_from_stats(stats_cursor,
                                                       'density_num',
                                                       'density_num')


def create_award_data():
    cursor = get_sql_interface(config['awards']['award_db'], no_conn=True)
    gen_awards(cursor)
