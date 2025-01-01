import networkx as nx

from data import data
from utils import config, get_logger


logger = get_logger(__name__)


def get_increment(minmax_config, max_val):
    config_range = float(minmax_config['max']) \
                 - float(minmax_config['min'])
    increment = config_range / max_val

    return increment


def get_attr_val(minmax_config, increment, val):
    value = float(minmax_config['min']) + increment*val
    return str(value)


def mapping(gv_graph):
    node_config = config['graph_image']['node']

    node_size_increment = get_increment(node_config['size'],
                                        data['max_in_endo_num'])
    logger.debug('Node size increment: %f', node_size_increment)

    node_hue_increment = get_increment(node_config['fill_color']['hue'],
                                       data['max_out_endo_num'])
    logger.debug('Node hue increment: %f', node_hue_increment)

    font_size_increment = get_increment(node_config['label']['font_size'],
                                        data['max_in_endo_num'])
    logger.debug('Font size increment: %f', font_size_increment)

    node_color_saturation_str = repr(float(node_config['fill_color']['saturation']))
    node_color_value_str = repr(float(node_config['fill_color']['value']))

    for node in gv_graph.nodes():

        node.attr['width'] = get_attr_val(node_config['size'],
                                          node_size_increment,
                                          gv_graph.in_degree(node))

        node.attr['fontsize'] = get_attr_val(node_config['label']['font_size'],
                                             font_size_increment,
                                             gv_graph.in_degree(node))
        logger.debug('Font size of "%s": %s', node, node.attr['fontsize'])

        node_color_hue_str = repr(node_hue_increment*gv_graph.out_degree(node))
        color_str = "{} {} {}".format(node_color_hue_str,
                                      node_color_saturation_str,
                                      node_color_value_str)
        node.attr['color'] = color_str

        node.attr['label'] = data['nation_name_dict'][node]

    logger.info('Data mapping successfully')


def generate_img():
    gv_graph = nx.drawing.nx_agraph.to_agraph(data.nx_graph)
    logger.debug('Created AGraph')

    graph_config = config['graph_image']
    gv_graph.graph_attr['size'] = graph_config['size']
    gv_graph.graph_attr['dpi'] = repr(float(graph_config['dpi']))
    gv_graph.graph_attr['outputorder'] = graph_config['output_order']
    gv_graph.graph_attr['nodesep'] = repr(float(graph_config['node_sep']))
    gv_graph.graph_attr['overlap'] = graph_config['overlap']
    gv_graph.graph_attr['overlap_scaling'] = repr(
                         float(graph_config['overlap_scaling']))
    gv_graph.graph_attr['bgcolor'] = graph_config['background_color']
    gv_graph.graph_attr['maxiter'] = str(graph_config['max_iter'])

    node_config = graph_config['node']
    gv_graph.node_attr['style'] = node_config['style']
    gv_graph.node_attr['shape'] = node_config['shape']
    gv_graph.node_attr['fixedsize'] = node_config['fixed_size']
    gv_graph.node_attr['fontname'] = node_config['label']['font_name']
    gv_graph.node_attr['fontcolor'] = node_config['label']['font_color']

    edge_config = graph_config['edge']
    gv_graph.edge_attr['penwidth'] = repr(float(edge_config['thickness']))
    gv_graph.edge_attr['arrowsize'] = repr(float(edge_config['arrow_size']))
    gv_graph.edge_attr['color'] = edge_config['color']
    gv_graph.graph_attr['splines'] = edge_config['type']

    mapping(gv_graph)

    gv_graph.draw(path=graph_config['cache_path'], prog=graph_config['prog'])
    logger.info('Created map image')
