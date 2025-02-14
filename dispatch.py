import time
import io
import re
from typing import Mapping

import requests

from utils import config, get_timestamp, round_str, get_logger
from utils import gen_list_table, gen_census_table, gen_center_td, gen_change_format
from utils import gen_text_list, wrap_nation_bbcode, get_value_from_list
from data import data

NS_API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"
NS_API_SLEEP = 0.8


logger = get_logger(__name__)


class NsDispatchUtil:
    def __init__(self, user_agent: str):
        self.session = requests.Session()
        self.session.headers = {"user-agent": user_agent}
        self.nation_name = None
        self.exec_token_regex = re.compile(r"<SUCCESS>(.+)</SUCCESS>")

    def login(self, nation_name: str, password: str) -> None:
        req_params = {"nation": nation_name, "q": "ping"}
        req_headers = {"X-Password": password}
        resp = self.session.get(
            NS_API_URL,
            headers=req_headers,
            params=req_params,
        )

        if resp.status_code == 403:
            logger.error(f"Incorrect password for dispatch nation {nation_name}")
            exit(1)

        self.nation_name = nation_name
        self.session.headers["X-Pin"] = resp.headers["X-Pin"]
        logger.info(f'Logged into dispatch nation "{nation_name}"')

    def send_req(self, req_body: Mapping[str, str]) -> None:
        resp = self.session.post(
            NS_API_URL,
            data=req_body | {"mode": "prepare"},
        )
        exec_token = self.exec_token_regex.search(resp.text).group(1)

        self.session.post(
            NS_API_URL, data=req_body | {"mode": "execute", "token": exec_token}
        )

    def add_dispatch(
        self, title: str, text: str, category: str, subcategory: str
    ) -> None:
        req_body = {
            "c": "dispatch",
            "dispatch": "add",
            "nation": self.nation_name,
            "title": title,
            "text": text,
            "category": category,
            "subcategory": subcategory,
        }
        self.send_req(req_body=req_body)

    def edit_dispatch(
        self, id: str, title: str, text: str, category: str, subcategory: str
    ) -> None:
        req_body = {
            "c": "dispatch",
            "dispatch": "edit",
            "dispatchid": id,
            "nation": self.nation_name,
            "title": title,
            "text": text,
            "category": category,
            "subcategory": subcategory,
        }
        self.send_req(req_body=req_body)


auth_conf = config["auth"]
dispatch_util = NsDispatchUtil(auth_conf["user_agent"])
dispatch_util.login(auth_conf["nation"], auth_conf["password"])


def upload_dispatch(ns, dispatch, title, category, subcategory, edit=None):
    subcategory_param_name = "subcategory-" + category
    params = {
        "edit": edit,
        "category": category,
        subcategory_param_name: subcategory,
        "dname": title,
        "message": dispatch,
        "submitbutton": "1",
    }

    ns.execute("lodge_dispatch", params)


def get_bbcode_placeholders():
    bbcode_placeholders = {}

    for item in config["dispatch"]["custom_bbcode"]:
        template_text = open(item["template_file"]).read()
        bbcode_placeholders[item["bbcode"]] = template_text

    return bbcode_placeholders


def process_dispatch(dispatch, placeholders):
    for placeholder in placeholders.items():
        dispatch = dispatch.replace(placeholder[0], placeholder[1])

    return dispatch


def get_placeholders(awards=False):
    placeholders = get_bbcode_placeholders()

    if awards:
        try:
            placeholders.update(
                {
                    "[most_avg_in_endos=0]": gen_center_td(
                        wrap_nation_bbcode(data["award_in_endo_rank"][0])
                    ),
                    "[most_avg_in_endos=1:11]": gen_list_table(
                        data["award_in_endo_rank"][1:11], 5
                    ),
                    "[most_avg_in_endos=12:52]": gen_list_table(
                        data["award_in_endo_rank"][12:52], 5
                    ),
                    "[most_avg_out_endos=0]": gen_center_td(
                        wrap_nation_bbcode(data["award_out_endo_rank"][0])
                    ),
                    "[most_avg_out_endos=1:11]": gen_list_table(
                        data["award_out_endo_rank"][1:11], 5
                    ),
                    "[most_avg_out_endos=12:52]": gen_list_table(
                        data["award_out_endo_rank"][12:52], 5
                    ),
                    "[most_given_endos=0]": gen_center_td(
                        wrap_nation_bbcode(data["award_given_endo_rank"][0])
                    ),
                    "[most_given_endos=1:11]": gen_list_table(
                        data["award_given_endo_rank"][1:11], 5
                    ),
                    "[most_given_endos=12:52]": gen_list_table(
                        data["award_given_endo_rank"][12:52], 5
                    ),
                    "[accu_crsdel_list]": gen_text_list(data["award_crsdel"]),
                    "[accu_wa_nations_list]": gen_text_list(data["award_wa_nations"]),
                    "[delegate]": config["data"]["delegate"],
                }
            )
        except KeyError as e:
            logger.error('Data "%s" does not exist', e)
    else:
        try:
            placeholders.update(
                {
                    "[timestamp]": get_timestamp("%a %b %d %Y %H:%M:%S %Z"),
                    "[endo_map_url]": data["endo_map_url"],
                    "[endo_map_small_url]": data["endo_map_small_url"],
                    "[new_wa_nations]": gen_text_list(data["new_wa_nations"]),
                    "[wa_nations]": gen_text_list(
                        list(data.nx_graph.nodes), noflag=True
                    ),
                    "[nations_notin_wa]": gen_text_list(
                        data["nations_notin_wa"], noflag=True
                    ),
                    "[wa_nation_num]": str(data["wa_nation_num"]),
                    "[wa_nation_num_change]": gen_change_format(
                        data["wa_nation_num_change"]
                    ),
                    "[perc_wa_regional_nation_num]": round_str(
                        data["perc_wa_to_region"]
                    ),
                    "[perc_wa_regional_nation_num_change]": gen_change_format(
                        data["perc_wa_regional_nation_num_change"]
                    ),
                    "[perc_wa_ns_wa]": round_str(data["perc_wa_to_ns_wa"]),
                    "[perc_wa_ns_wa_change]": gen_change_format(
                        data["perc_wa_ns_wa_change"]
                    ),
                    "[regional_nation_num]": str(data["regional_nation_num"]),
                    "[regional_nation_num_change]": gen_change_format(
                        data["regional_nation_num_change"]
                    ),
                    "[perc_regional_nation_num_ns]": round_str(
                        data["perc_regional_nation_num_ns"]
                    ),
                    "[perc_regional_nation_num_ns_change]": gen_change_format(
                        data["perc_regional_nation_num_ns_change"]
                    ),
                    "[max_in_endo_nation]": wrap_nation_bbcode(
                        data["max_in_endo_nation"]
                    ),
                    "[delegate]": wrap_nation_bbcode(config["data"]["delegate"]),
                    "[max_in_endo_num]": str(data["max_in_endo_num"]),
                    "[max_in_endo_num_change]": gen_change_format(
                        data["max_in_endo_num_change"]
                    ),
                    "[perc_max_in_endo_num_wa]": round_str(
                        data["perc_max_in_endo_num_wa"]
                    ),
                    "[perc_max_in_endo_num_wa_change]": gen_change_format(
                        data["perc_max_in_endo_num_wa_change"]
                    ),
                    "[SPCG_list]": gen_text_list(config["data"]["SPCG"]),
                    "[SPCG_table_list]": gen_list_table(config["data"]["SPCG"], 5),
                    "[SPCG_num]": str(len(config["data"]["SPCG"])),
                    "[SPCG_census]": gen_census_table(
                        data["SPCG_census"], 0, disp_rank=False
                    ),
                    "[SPCG_avg_in_endo_num]": round_str(data["SPCG_avg_in_endo_num"]),
                    "[SPCG_avg_in_endo_num_change]": gen_change_format(
                        data["SPCG_avg_in_endo_num_change"]
                    ),
                    "[SPCG_endo_cap]": round_str(data["SPCG_endo_cap"], "%.0f", 1),
                    "[SPCG_endo_cap_below_delegate]": str(
                        config["data"]["SPCG_endo_cap_below_delegate"]
                    ),
                    "[SPCG_endo_cap_ref]": wrap_nation_bbcode(
                        data["SPCG_endo_cap_ref"]
                    ),
                    "[SPCG_endo_cap_ref_endo]": str(data["SPCG_endo_cap_ref_endo"]),
                    "[endo_cap]": str(data["endo_cap"]),
                    "[endo_cap_ref]": wrap_nation_bbcode(data["endo_cap_ref"]),
                    "[endo_caution_line]": round_str(
                        data["endo_caution_line"], "%.0f", 1
                    ),
                    "[endo_caution_line_perc]": str(
                        config["data"]["endo_caution_line_perc"]
                    ),
                    "[crsdel_list]": gen_list_table(data["crsdel_list"], 5),
                    "[crsdel_num]": str(data["crsdel_num"]),
                    "[crsdel_num_change]": gen_change_format(data["crsdel_num_change"]),
                    "[perc_crsdel_num_wa]": round_str(data["perc_crsdel_num_wa"]),
                    "[perc_crsdel_num_wa_change]": gen_change_format(
                        data["perc_crsdel_num_wa_change"]
                    ),
                    "[nation_notendo_crsdel]": gen_text_list(
                        data["nation_notendo_crsdel"], noflag=True
                    ),
                    "[nation_notendo_nation]": gen_text_list(
                        data["nation_notendo_nation"], noflag=True
                    ),
                    "[mention_nation]": wrap_nation_bbcode(
                        config["data"]["mention_nation"]
                    ),
                    "[out_endo_census]": gen_census_table(
                        data["out_endo_census"][:85], 0
                    ),
                    "[in_endo_census]": gen_census_table(
                        data["in_endo_census"][:85],
                        0,
                        highlight_column_idx=[0, 1],
                        highlight_check_idx=4,
                    ),
                    "[endotarting_census]": gen_census_table(
                        data["endotarting_census"][:200], 0
                    ),
                    "[endo_num]": str(data["endo_num"]),
                    "[endo_num_change]": gen_change_format(data["endo_num_change"]),
                    "[density_num]": round_str(data["density_num"]),
                    "[density_num_change]": gen_change_format(
                        data["density_num_change"]
                    ),
                }
            )
        except KeyError as e:
            logger.error('Data "%s" does not exist', e, exc_info=True)

        if config["delegate_transition"] is True:
            try:
                placeholders.update(
                    {
                        "[delegate_elect_in_endo_num]": str(
                            get_value_from_list(
                                data["in_endo_sorted_list"], config["data"]["delegate"]
                            )
                        ),
                        "[delegate_elect_in_endo_num_change]": gen_change_format(
                            [
                                i[2]
                                for i in data["in_endo_census"]
                                if i[0] == config["data"]["delegate"]
                            ][0]
                        ),
                    }
                )
            except KeyError as e:
                logger.error('Data "%s" does not exist', e)

    return placeholders


def update_dispatch():
    template_list = config["dispatch"]["dispatches"]
    placeholders = get_placeholders()

    for conf in template_list:
        template_filename = conf["template_file"]
        try:
            template = io.open(template_filename, "r", encoding="utf8").read()
            logger.debug("Opened template file: %s", template_filename)
        except IOError:
            logger.error("Cannot open template file: %s", template_filename)
            exit(1)

        text = process_dispatch(template, placeholders)
        logger.debug("Processed dispatch content:\n%s", text)

        dispatch_util.edit_dispatch(
            conf["edit_id"],
            conf["title"],
            text,
            conf["category"],
            conf["subcategory"],
        )

        logger.info("Edited dispatch: %s", template_filename)

        time.sleep(NS_API_SLEEP)


def create_award_dispatch():
    conf = config["awards"]
    template_filename = conf["template_file"]
    placeholders = get_placeholders(awards=True)

    try:
        template = open(template_filename).read()
        logger.debug("Opened award template file: %s", template_filename)
    except IOError:
        logger.error("Cannot open award template file: %s", template_filename)
        exit(1)

    text = process_dispatch(template, placeholders)
    logger.debug("Processed dispatch content:\n%s", text)

    dispatch_util.add_dispatch(
        conf["title"],
        text,
        conf["category"],
        conf["subcategory"],
    )

    logger.info("Created dispatch: %s", template_filename)
