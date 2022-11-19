from google.oauth2 import service_account
from googleapiclient import discovery, http

from utils import config, round_str, get_timestamp
from utils import get_logger, get_value_from_list, add_timestamp
from data import data


CREDENTIAL_FILENAME = 'sheets.googleapis.com-tsp-wa-init.json'

SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']


logger = get_logger(__name__)


def get_credentials(scopes):
    return service_account.Credentials.from_service_account_file(
        config['google_service']['cred_path'], scopes=scopes
        )


def get_service(service_name, version, scopes):
    credentials = get_credentials(scopes)
    service = discovery.build(service_name, version, credentials=credentials, cache_discovery=False)
    return service


def get_stats_values():
    values = [
        get_timestamp('%Y/%m/%d'),

        str(data['regional_nation_num']),
        round_str(data['perc_regional_nation_num_ns']),

        str(data['wa_nation_num']),
        round_str(data['perc_wa_to_region']),
        round_str(data['perc_wa_to_ns_wa']),

        str(data['nation_name_dict'][data['max_in_endo_nation']]),
        str(data['max_in_endo_num']),
        round_str(data['perc_max_in_endo_num_wa']),

        str(data['crsdel_num']),
        round_str(data['perc_crsdel_num_wa']),

        str(data['endo_num']),

        round_str(data['density_num'])
    ]

    logger.debug('Stats sheet values: %r', values)
    return values


def get_endocap_values():
    values = [
        get_timestamp('%Y/%m/%d'),
		str(data['endo_cap']),
        str(config['data']['endo_cap_perc']),
        data['nation_name_dict'][data['endo_cap_ref']],
        str(data['endo_cap_ref_endo'])
    ]

    logger.debug('Endo cap sheet values: %r', values)
    return values


def get_SPCG_endocap_values():
    values = [
        get_timestamp('%Y/%m/%d'),
		str(data['SPCG_endo_cap']),
        str(config['data']['SPCG_endo_cap_below_delegate']),
        data['nation_name_dict'][data['SPCG_endo_cap_ref']],
        str(data['SPCG_endo_cap_ref_endo']),
        str(data['SPCG_avg_in_endo_num'])
    ]

    logger.debug('SPCG Endo cap sheet values: %r', values)
    return values


def get_crs_values():
    values = [
        get_timestamp('%Y/%m/%d'),

        str(data['crs_in_endo_sorted_list'][0][1]),
        str(data['crs_in_endo_sorted_list'][-1][1]),
        str(data['crs_avg_in_endo_num'])
    ]

    logger.debug('CRS sheet values: %r', values)
    return values


def get_delegate_transition_values():
    values = [
        get_timestamp('%Y/%m/%d'),

        str(data['max_in_endo_num']),
        str(get_value_from_list(data['in_endo_sorted_list'], config['data']['delegate']))
    ]

    logger.debug('Delegate transition values: %r', values)
    return values


def append_value_sheet(service, sheet_id, range, values):
    body = {"range": range,
            "values": [values],
            "majorDimension": config['google_service']['major_dimension']}

    service.values().append(spreadsheetId=sheet_id,
                            range=range,
                            body=body,
                            valueInputOption="USER_ENTERED").execute()


def update_sheet():
    service = get_service('sheets', 'v4', SHEETS_SCOPES).spreadsheets()

    range_config = config['google_service']['ranges']
    sheet_config = config['google_service']['sheet_ids']

    stats_values = get_stats_values()
    append_value_sheet(service, sheet_config['general'],
                       range_config['stats'], stats_values)
    logger.info('Updated stats sheet')

    crs_values = get_crs_values()
    append_value_sheet(service, sheet_config['general'],
                       range_config['crs'], crs_values)
    logger.info('Updated crs sheet')

    endocap_values = get_endocap_values()
    append_value_sheet(service, sheet_config['general'],
                       range_config['endo_cap'], endocap_values)

    SPCG_endocap_values = get_SPCG_endocap_values()
    append_value_sheet(service, sheet_config['general'],
                       range_config['SPCG_stats'], SPCG_endocap_values)

    if config['delegate_transition']:
        delegate_transition_values = get_delegate_transition_values()
        append_value_sheet(service, sheet_config['delegate_transition'],
                           range_config['delegate_transition'],
                           delegate_transition_values)
        logger.info('Updated delegate transition sheet')


def get_shareable_link(service, id):
    permission = {'type': 'anyone', 'role': 'reader'}
    service.permissions().create(fileId=id,
                                 body=permission).execute()
    logger.info('Added reader role to everyone')

    respond = service.files().get(fileId=id,
                                  fields='webViewLink').execute()
    shareable_link = respond['webViewLink']
    logger.info('Got shareable link: "%s"', shareable_link)

    return shareable_link


def upload_image():
    service = get_service('drive', 'v3', DRIVE_SCOPES)

    media = http.MediaFileUpload(config['final_image']['save_path'],
                                 mimetype='image/png', resumable=True)

    metadata = {'name': add_timestamp(config['google_service']['portrait_name']),
                'parents': [config['google_service']['portrait_folder_id']]}

    file_id = service.files().create(body=metadata, media_body=media,
                                     fields='id').execute()['id']
    logger.info('Uploaded image to Drive')

    data['endo_map_url'] = get_shareable_link(service, file_id)
