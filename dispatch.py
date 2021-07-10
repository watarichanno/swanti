import time
import sys
import io

import utils
from utils import config, get_timestamp, round_str, get_logger
from utils import gen_list_table, gen_census_table, gen_center_td, gen_change_format
from utils import gen_text_list, wrap_nation_bbcode, get_value_from_list
from data import data
import nsinterface


logger = get_logger(__name__)


def upload_dispatch(ns, dispatch, title, category, subcategory, edit=None):
    subcategory_param_name = "subcategory-" + category
    params = {'edit': edit,
              'category': category,
              subcategory_param_name: subcategory,
              'dname': title,
              'message': dispatch,
              'submitbutton': '1'}

    ns.execute('lodge_dispatch', params)


def get_bbcode_placeholders():
    bbcode_placeholders = {}

    for item in config['dispatch']['custom_bbcode']:
        template_text = open(item['template_file']).read()
        bbcode_placeholders[item['bbcode']] = template_text

    return bbcode_placeholders


def process_dispatch(dispatch, placeholders):
    for placeholder in placeholders.items():
        dispatch = dispatch.replace(placeholder[0], placeholder[1])

    return dispatch


def get_placeholders(awards=False):
    placeholders = get_bbcode_placeholders()

    if awards:
        try:
             placeholders.update({
                '[most_avg_in_endos=0]': gen_center_td(wrap_nation_bbcode(data['award_in_endo_rank'][0])),
                '[most_avg_in_endos=1:11]': gen_list_table(data['award_in_endo_rank'][1:11], 5),
                '[most_avg_in_endos=12:52]': gen_list_table(data['award_in_endo_rank'][12:52], 5),
                '[most_avg_out_endos=0]': gen_center_td(wrap_nation_bbcode(data['award_out_endo_rank'][0])),
                '[most_avg_out_endos=1:11]': gen_list_table(data['award_out_endo_rank'][1:11], 5),
                '[most_avg_out_endos=12:52]': gen_list_table(data['award_out_endo_rank'][12:52], 5),
                '[most_given_endos=0]': gen_center_td(wrap_nation_bbcode(data['award_given_endo_rank'][0])),
                '[most_given_endos=1:11]': gen_list_table(data['award_given_endo_rank'][1:11], 5),
                '[most_given_endos=12:52]': gen_list_table(data['award_given_endo_rank'][12:52], 5),
                '[accu_crsdel_list]': gen_text_list(data['award_crsdel']),
                '[accu_wa_nations_list]': gen_text_list(data['award_wa_nations']),
                '[delegate]': config['data']['delegate']
            })
        except KeyError as e:
            logger.error('Data "%s" does not exist', e)
    else:
        try:
            placeholders.update({
                '[timestamp]': get_timestamp("%a %b %d %Y %H:%M:%S %Z"),

                '[endo_map_url]': data['endo_map_url'],
                '[endo_map_small_url]': data['endo_map_small_url'],

                '[new_wa_nations]': gen_text_list(data['new_wa_nations']),
                '[wa_nations]': gen_text_list(list(data.nx_graph.nodes), noflag=True),
                '[nations_notin_wa]': gen_text_list(data['nations_notin_wa'], noflag=True),

                '[wa_nation_num]': str(data['wa_nation_num']),
                '[wa_nation_num_change]': gen_change_format(data['wa_nation_num_change']),
                '[perc_wa_regional_nation_num]': round_str(data['perc_wa_to_region']),
                '[perc_wa_regional_nation_num_change]': gen_change_format(data['perc_wa_regional_nation_num_change']),
                '[perc_wa_ns_wa]': round_str(data['perc_wa_to_ns_wa']),
                '[perc_wa_ns_wa_change]': gen_change_format(data['perc_wa_ns_wa_change']),

                '[regional_nation_num]': str(data['regional_nation_num']),
                '[regional_nation_num_change]': gen_change_format(data['regional_nation_num_change']),
                '[perc_regional_nation_num_ns]': round_str(data['perc_regional_nation_num_ns']),
                '[perc_regional_nation_num_ns_change]': gen_change_format(data['perc_regional_nation_num_ns_change']),

                '[max_in_endo_nation]': wrap_nation_bbcode(data['max_in_endo_nation']),
                '[delegate]': wrap_nation_bbcode(config['data']['delegate']),
                '[max_in_endo_num]': str(data['max_in_endo_num']),
                '[max_in_endo_num_change]': gen_change_format(data['max_in_endo_num_change']),
                '[perc_max_in_endo_num_wa]': round_str(data['perc_max_in_endo_num_wa']),
                '[perc_max_in_endo_num_wa_change]': gen_change_format(data['perc_max_in_endo_num_wa_change']),

                '[crs_list]': gen_text_list(config['data']['crs']),
                '[crs_table_list]': gen_list_table(config['data']['crs'], 5),
                '[crs_num]': str(len(config['data']['crs'])),
                '[crs_census]': gen_census_table(data['crs_census'], 0, disp_rank=False),
                '[crs_avg_in_endo_num]': round_str(data['crs_avg_in_endo_num']),
                '[crs_avg_in_endo_num_change]': gen_change_format(data['crs_avg_in_endo_num_change']),

                '[SPCG_list]': gen_text_list(config['data']['SPCG']),
                '[SPCG_table_list]': gen_list_table(config['data']['SPCG'], 5),
                '[SPCG_num]': str(len(config['data']['SPCG'])),
                '[SPCG_census]': gen_census_table(data['SPCG_census'], 0, disp_rank=False),
                '[SPCG_avg_in_endo_num]': round_str(data['SPCG_avg_in_endo_num']),
                '[SPCG_avg_in_endo_num_change]': gen_change_format(data['SPCG_avg_in_endo_num_change']),
                '[SPCG_endo_cap]': round_str(data['SPCG_endo_cap'], '%.0f', 1),
                '[SPCG_endo_cap_perc]': str(config['data']['SPCG_endo_cap_perc']),
                '[SPCG_endo_cap_ref]': wrap_nation_bbcode(data['SPCG_endo_cap_ref']),
                '[SPCG_endo_cap_ref_endo]': str(data['SPCG_endo_cap_ref_endo']),

                '[endo_cap]': round_str(data['endo_cap'], '%.0f', 1),
                '[endo_cap_perc]': str(config['data']['endo_cap_perc']),
                '[endo_cap_ref]': wrap_nation_bbcode(data['endo_cap_ref']),
                '[endo_cap_ref_endo]': str(data['endo_cap_ref_endo']),

                '[crsdel_list]': gen_list_table(data['crsdel_list'], 5),
                '[crsdel_num]': str(data['crsdel_num']),
                '[crsdel_num_change]': gen_change_format(data['crsdel_num_change']),
                '[perc_crsdel_num_wa]': round_str(data['perc_crsdel_num_wa']),
                '[perc_crsdel_num_wa_change]': gen_change_format(data['perc_crsdel_num_wa_change']),
                '[nation_notendo_crsdel]': gen_text_list(data['nation_notendo_crsdel'], noflag=True),
                '[nation_notendo_nation]': gen_text_list(data['nation_notendo_nation'], noflag=True),
                '[mention_nation]': wrap_nation_bbcode(config['data']['mention_nation']),

                '[out_endo_census]': gen_census_table(data['out_endo_census'][:85], 0),
                '[in_endo_census]': gen_census_table(data['in_endo_census'][:85], 0,
                                                 highlight_column_idx=[0, 1],
                                                 highlight_check_idx=4),
                '[endotarting_census]': gen_census_table(data['endotarting_census'][:200], 0),

                '[endo_num]': str(data['endo_num']),
                '[endo_num_change]': gen_change_format(data['endo_num_change']),

                '[density_num]': round_str(data['density_num']),
                '[density_num_change]': gen_change_format(data['density_num_change'])
             })
        except KeyError as e:
            logger.error('Data "%s" does not exist', e, exc_info=True)

        if config['delegate_transition'] is True:
            try:
                placeholders.update({
                    '[delegate_elect_in_endo_num]': str(get_value_from_list(data['in_endo_sorted_list'],
                                                        config['data']['delegate'])),
                    '[delegate_elect_in_endo_num_change]': gen_change_format(
                                                           [i[2] for i in data['in_endo_census']
                                                           if i[0] == config['data']['delegate']][0]),
                })
            except KeyError as e:
                logger.error('Data "%s" does not exist', e)

    return placeholders


def update_dispatch():
    dispatch_template_list = config['dispatch']['dispatches']
    ns = nsinterface.create_nsii_instance()
    placeholders = get_placeholders()

    for dispatch_config in dispatch_template_list:
        template_filename = dispatch_config['template_file']
        try:
            dispatch = io.open(template_filename, 'r', encoding='utf8').read()
            logger.info('Opened template file: %s', template_filename)
        except IOError:
            logger.error('Cannot open template file: %s', template_filename)
            sys.exit()

        dispatch = process_dispatch(dispatch, placeholders)
        logger.info('Processed dispatch: %s', template_filename)
        logger.debug('Processed dispatch content:\n%s', dispatch)

        upload_dispatch(ns,
                        dispatch,
                        dispatch_config['title'],
                        dispatch_config['category'],
                        dispatch_config['subcategory'],
                        dispatch_config['edit_id'])
        logger.info('Uploaded dispatch: %s', template_filename)

        time.sleep(6)


def create_award_dispatch():
    dispatch_config = config['awards']
    template_filename = dispatch_config['template_file']
    ns = nsinterface.create_nsii_instance()
    placeholders = get_placeholders(awards=True)

    try:
        dispatch = open(template_filename).read()
        logger.info('Opened award template file: %s', template_filename)
    except IOError:
        logger.error('Cannot open award template file: %s', template_filename)
        sys.exit()

    dispatch = process_dispatch(dispatch, placeholders)
    logger.info('Processed dispatch: %s', template_filename)
    logger.debug('Processed dispatch content:\n%s', dispatch)

    upload_dispatch(ns,
                    dispatch,
                    dispatch_config['title'],
                    dispatch_config['category'],
                    dispatch_config['subcategory'])
    logger.info('Uploaded dispatch: %s', template_filename)
