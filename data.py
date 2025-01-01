import sys
import time
import operator
import gzip
import xml.etree.cElementTree as ElementTree

import networkx as nx

from utils import config
from utils import get_datadump
from utils import get_sql_interface
from utils import get_logger

logger = get_logger(__name__)


def add_endo(endo_nation, nation_name, nx_graph, regional_nations_set):
    if endo_nation in regional_nations_set:
        nx_graph.add_edge(endo_nation, nation_name)


def load_data(file_name):
    try:
        data_dump = gzip.open(file_name, "rb")
        logger.info('Opened data dump file "%s"', file_name)
    except IOError:
        logger.error("Cannot open data dump file. Exit")
        sys.exit()

    try:
        root = ElementTree.parse(data_dump).getroot()
        logger.info("Parsed XML tree")
    except ElementTree.ParseError as e:
        logger.error("XML parse error %d at line %d", e.code, e.position[0])
        sys.exit()

    return root


def build_graph(file_name):
    root = load_data(file_name)

    nx_graph = nx.DiGraph()
    logger.info("Initialized directional graph")

    ns_wa_num = 0
    regional_nation_num = 0
    nation_name_dict = {}

    i = build_regional_nation_set(root)
    regional_nations_set = i[0]
    regional_nation_num = i[1]
    ns_wa_num = i[2]
    ns_nation_num = i[3]
    notin_wa = i[4]
    active_wa = i[5]

    is_in_region = False

    wa_nations = set()

    for nation in root:
        if nation.find("REGION").text == config["data"]["region"]:
            is_in_region = True

            if nation.find("UNSTATUS").text.find("WA") != -1:
                nation_name = nation.find("NAME").text
                lower_nation_name = nation_name.lower()

                nation_name_dict[lower_nation_name] = nation_name
                wa_nations.add(lower_nation_name)

                endo_list = nation.find("ENDORSEMENTS").text

                if endo_list is None:
                    nx_graph.add_node(lower_nation_name)
                elif "," not in endo_list:
                    endo_nation = endo_list.replace("_", " ")
                    add_endo(
                        endo_nation, lower_nation_name, nx_graph, regional_nations_set
                    )
                elif "," in endo_list:
                    for endo_nation in endo_list.split(","):
                        endo_nation = endo_nation.replace("_", " ")
                        add_endo(
                            endo_nation,
                            lower_nation_name,
                            nx_graph,
                            regional_nations_set,
                        )

        elif is_in_region:
            break

    logger.debug("NS nation num is %d", ns_wa_num)
    logger.debug("Regional nation num is %d", regional_nation_num)

    logger.info("Finished building graph")
    return (
        nx_graph,
        regional_nation_num,
        ns_wa_num,
        ns_nation_num,
        nation_name_dict,
        notin_wa,
        active_wa,
        wa_nations,
    )


def build_regional_nation_set(root):
    regional_nation_set = set()
    notin_wa = []
    active_wa = []
    regional_nation_num = 0
    ns_wa_num = 0
    ns_nation_num = 0

    for nation in root:
        ns_nation_num += 1

        nation_name = nation.find("NAME").text.lower()

        if nation.find("UNSTATUS").text.find("WA") != -1:
            ns_wa_num += 1

            if nation.find("REGION").text == config["data"]["region"]:
                regional_nation_num += 1
                if time.time() - int(nation.find("LASTLOGIN").text) < 259200:
                    active_wa.append(nation_name)

                regional_nation_set.add(nation_name)

        elif nation.find("REGION").text == config["data"]["region"]:
            regional_nation_num += 1

            if time.time() - int(nation.find("LASTLOGIN").text) < 52800:
                notin_wa.append(nation_name)

    logger.info("Finished building nation set")
    return (
        regional_nation_set,
        regional_nation_num,
        ns_wa_num,
        ns_nation_num,
        notin_wa,
        active_wa,
    )


# get a list of nations that endorse the entire CRS
def get_crsdel_endorsers(nx_graph):
    crsdel_endorsers = []

    for nation in nx_graph.nodes():
        endorsed_crsdel_nations = [
            endorsed
            for endorsed in nx_graph.successors(nation)
            if endorsed in config["data"]["crsdel"]
        ]
        if set(endorsed_crsdel_nations) == set(config["data"]["crsdel"]):
            crsdel_endorsers.append(nation)

    logger.debug("Created crs+del list: %r", crsdel_endorsers)
    return crsdel_endorsers


def get_SPCG_avg_in_endo(nx_graph):
    avg_in_endo = 0

    total = 0
    number_of_SPCG_mem = 0
    for nation in config["data"]["SPCG"]:
        total += nx_graph.in_degree(nation)
        number_of_SPCG_mem += 1

    avg_in_endo = float(total) / float(number_of_SPCG_mem)

    logger.debug("Got avg in endo of SPCG: %f", avg_in_endo)
    return avg_in_endo


# Get a dict of nations and their out-endos
def get_out_endo_dict(nx_graph):
    out_endo_dict = {}
    for nation in nx_graph.nodes:
        out_endo_list = [out_endo for out_endo in nx_graph.successors(nation)]
        out_endo_dict[nation] = out_endo_list

    return out_endo_dict


def get_SPCG_in_endo(data):
    SPCG_in_endo = []

    for i in data["in_endo_sorted_list"]:
        nation = i[0]

        if nation in config["data"]["SPCG"]:
            in_endo_num = i[1]
            SPCG_in_endo.append([nation, in_endo_num])

    return SPCG_in_endo


def analyse(data, nx_graph):
    data["wa_nation_num"] = nx_graph.number_of_nodes()

    logger.debug("Calculated WA nation num: %d", data["wa_nation_num"])

    # =====================================================================

    data["perc_wa_to_region"] = (
        float(data["wa_nation_num"]) / float(data["regional_nation_num"]) * 100
    )

    logger.debug(
        "Calculated %% WAs to regional nation num: %f", data["perc_wa_to_region"]
    )

    # =====================================================================

    data["perc_wa_to_ns_wa"] = (
        float(data["wa_nation_num"]) / float(data["ns_wa_num"]) * 100
    )

    logger.debug("Calculated %% WAs to NS WA nation num: %f", data["perc_wa_to_ns_wa"])

    # =====================================================================

    data["perc_regional_nation_num_ns"] = (
        float(data["regional_nation_num"]) / float(data["ns_nation_num"]) * 100
    )

    logger.debug(
        "Calculated %% regional nation num to NS nation num: %f",
        data["perc_regional_nation_num_ns"],
    )

    # =====================================================================

    data["endo_num"] = nx_graph.number_of_edges()

    logger.debug("Calculated number of endorsements: %d", data["endo_num"])

    # =====================================================================

    data["out_endo_sorted_list"] = sorted(
        nx_graph.out_degree, key=operator.itemgetter(1), reverse=True
    )

    logger.debug("Created out-endo sorted_list: %r", data["out_endo_sorted_list"])

    # =====================================================================

    data["max_out_endo_nation"] = data["out_endo_sorted_list"][0][0]

    logger.debug("Determined nation with max out-endo: %s", data["max_out_endo_nation"])

    # =====================================================================

    data["max_out_endo_num"] = data["out_endo_sorted_list"][0][1]

    logger.debug("Determined max out-endo: %d", data["max_out_endo_num"])

    # =====================================================================

    data["out_endo_dict"] = get_out_endo_dict(nx_graph)

    # =====================================================================

    data["generated_influence_dict"] = {
        nation: 1 + nx_graph.out_degree(nation) * 2 for nation in nx_graph.nodes
    }

    logger.debug(
        "Created generated influence dict:\n%r", data["generated_influence_dict"]
    )

    # =====================================================================

    data["in_endo_sorted_list"] = sorted(
        nx_graph.in_degree, key=operator.itemgetter(1), reverse=True
    )

    logger.debug("Created in-endo sorted_list: %r", data["in_endo_sorted_list"])

    # =====================================================================

    data["max_in_endo_nation"] = data["in_endo_sorted_list"][0][0]

    logger.debug("Determined nation with max in-endo: %r", data["max_in_endo_nation"])

    # =====================================================================

    data["max_in_endo_num"] = data["in_endo_sorted_list"][0][1]

    logger.debug("Determined max in-endo: %d", data["max_in_endo_num"])

    # =====================================================================

    data["gained_influence_dict"] = {
        nation: 1 + nx_graph.in_degree(nation) * 2 for nation in nx_graph.nodes
    }

    logger.debug("Created gained influence dict:\n%r", data["gained_influence_dict"])

    # =====================================================================

    data["perc_max_in_endo_num_wa"] = (
        float(data["max_in_endo_num"]) / float(data["wa_nation_num"]) * 100
    )

    logger.debug(
        "Determined %% of nations that endorse the delegate: %f",
        data["perc_max_in_endo_num_wa"],
    )

    # =====================================================================

    data["crsdel_list"] = get_crsdel_endorsers(nx_graph)

    # =====================================================================

    data["crsdel_num"] = len(data["crsdel_list"])

    logger.debug("Determined crs+del list length: %d", data["crsdel_num"])

    # =====================================================================

    data["perc_crsdel_num_wa"] = (
        float(data["crsdel_num"]) / float(data["wa_nation_num"]) * 100
    )

    logger.debug(
        "Determined %% of nations in crs+del list: %f", data["perc_crsdel_num_wa"]
    )

    # =====================================================================

    data["nation_notendo_crsdel"] = list(
        set(nx_graph.nodes) - (set(data["crsdel_list"]) | set(config["data"]["crsdel"]))
    )

    logger.debug(
        "Created nations not endorse crs+del list: %r", data["nation_notendo_crsdel"]
    )

    # =====================================================================

    data["nation_notendo_nation"] = [
        i
        for i in nx_graph.nodes
        if config["data"]["mention_nation"] not in nx_graph.successors(i)
    ]
    data["nation_notendo_nation"].remove(config["data"]["mention_nation"])

    # =====================================================================

    not_endo_nations = set(data["nation_notendo_nation"])
    active_wa_nations = set(data["nations_active_wa"])
    recipients = list(not_endo_nations & active_wa_nations)

    TELEGRAM_LINK = (
        "https://www.nationstates.net/page=compose_telegram/tgto={}?message={}\n"
    )
    TELEGRAM_TEMPLATE = "%TEMPLATE-27681655%"

    telegram_links = []
    current_link_recipients = []
    for recipient in recipients:
        current_link_recipients.append(recipient.replace(" ", "_"))
        if len(current_link_recipients) == 6:
            telegram_links.append(
                TELEGRAM_LINK.format(
                    ",".join(current_link_recipients), TELEGRAM_TEMPLATE
                )
            )
            current_link_recipients = []

    with open("telegram_links.txt", "w") as f:
        f.writelines(telegram_links)

    # =====================================================================

    data["density_num"] = float(nx.density(nx_graph)) * 100

    logger.debug("Determined graph density: %f", data["density_num"])

    # =====================================================================

    if not config["data"]["SPCG"]:
        data["SPCG_in_endo_sorted_list"] = []
        data["SPCG_avg_in_endo_num"] = 0
    else:
        data["SPCG_in_endo_sorted_list"] = get_SPCG_in_endo(data)
        data["SPCG_avg_in_endo_num"] = get_SPCG_avg_in_endo(nx_graph)

    logger.debug("SPCG endo list: %r", data["SPCG_in_endo_sorted_list"])
    logger.debug("SPCG average in endo: %f", data["SPCG_avg_in_endo_num"])

    # ==========================================================

    lowest_spcg_nation = data["SPCG_in_endo_sorted_list"][-1]
    data["endo_cap_ref"] = lowest_spcg_nation[0]
    lowest_spcg_nation_endo = lowest_spcg_nation[1]

    data["endo_cap"] = lowest_spcg_nation_endo
    data["endo_caution_line"] = lowest_spcg_nation_endo * config["data"]["endo_caution_line_perc"] / 100

    logger.debug("Endo cap: %f", data["endo_cap"])
    logger.debug("Endo cap ref: %s", data["endo_cap_ref"])
    logger.debug("Endo caution line: %f", data["endo_caution_line"])

    # =====================================================================

    SPCG_ref_nation = data["max_in_endo_nation"]
    SPCG_ref_endo = data["max_in_endo_num"]
    SPCG_endo_cap = SPCG_ref_endo - config["data"]["SPCG_endo_cap_below_delegate"]
    data["SPCG_endo_cap"] = SPCG_endo_cap
    data["SPCG_endo_cap_ref"] = SPCG_ref_nation
    data["SPCG_endo_cap_ref_endo"] = SPCG_ref_endo

    logger.debug("SPCG Endo cap: %f", data["SPCG_endo_cap"])
    logger.debug("SPCG Endo cap ref: %s", data["SPCG_endo_cap_ref"])
    logger.debug("SPCG Endo cap ref endo: %d", data["SPCG_endo_cap_ref_endo"])

    logger.info("Finished graph analysis")


class Data(object):
    def __init__(self):
        get_datadump()

        self.data = {}

        output = build_graph(config["data"]["dump_file"])
        self.nx_graph = output[0]
        self.data["regional_nation_num"] = output[1]
        self.data["ns_wa_num"] = output[2]
        self.data["ns_nation_num"] = output[3]
        self.data["nation_name_dict"] = output[4]
        self.data["nations_notin_wa"] = output[5]
        self.data["nations_active_wa"] = output[6]
        self.data["wa_nations"] = output[7]
        analyse(self.data, self.nx_graph)

        self.data["endo_map_url"] = ""
        self.data["endo_map_small_url"] = ""

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, item, value):
        self.data[item] = value


data = Data()
