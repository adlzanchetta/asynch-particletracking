import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from defineDistances_lib import DistancesDefiner
from def_lib import ArgumentsManager
from plots_lib import GraphsPlotter
import numpy as np
import datetime
import pickle
import random
import sys
import os


# ###################################################### HELP ######################################################## #

if '-h' in sys.argv:
    print("Usage: python barplot.py -in_contrib_dict IN_DICT -in_rvr IN_RVR -in_lengths IN_LENGTHS -out_hydrograph OUT_HYD")
    print("  IN_DICT    : File path for input hydrograph binary file.")
    print("  IN_RVR     : File path for .rvr describing the topology of the network.")
    print("  IN_LENGTHS : File path for .csv describing the lengths of the network.")
    print("  OUT_HYD    : File path for output hydrograph image file.")
    quit()

# ###################################################### ARGS ######################################################## #

# get arguments
input_hdict_fpath_arg = ArgumentsManager.get_str(sys.argv, '-in_contrib_dict')
input_rvr_fpath_arg = ArgumentsManager.get_str(sys.argv, '-in_rvr')
links_length_file_path = ArgumentsManager.get_str(sys.argv, '-in_lengths')
output_hpict_fpath_arg = ArgumentsManager.get_str(sys.argv, '-out_hydrograph')
y_limit_arg = ArgumentsManager.get_int(sys.argv, "-y_lim")

# basic checks
if input_hdict_fpath_arg is None:
    print("Missing '-in_contrib_dict' argument.")
    quit()
if input_rvr_fpath_arg is None:
    print("Missing '-in_rvr' argument.")
    quit()
if links_length_file_path is None:
    print("Missing '-in_lengths' argument.")
    quit()
if output_hpict_fpath_arg is None:
    print("Missing '-out_hydrograph' argument.")
    quit()

# ###################################################### DEFS ######################################################## #


def read_topo(rvr_fpath):
    """
    Reads .rvr file and converts it into into a dictionary.
    :param rvr_fpath:
    :return: Dictionary of integers with format "link_id":[contr_link_id1, contr_link_id2, contr_link_id3, ...]
    """

    return_dict = {}
    with open(rvr_fpath, "r+") as rfile:
        num_links = None
        last_linkid = None
        for cur_line in rfile:
            cur_line_clear = cur_line.strip()

            # ignore blank lines
            if cur_line_clear == "":
                continue

            # get header
            if num_links is None:
                num_links = int(cur_line_clear)
                continue

            cur_line_split = cur_line_clear.split(" ")

            # get link id
            if (len(cur_line_split) == 1) and (last_linkid is None):
                last_linkid = int(cur_line_split[0])
                continue

            # get parent links
            if last_linkid is not None:

                if len(cur_line_split) == 1:
                    return_dict[last_linkid] = None
                else:
                    return_dict[last_linkid] = [int(v) for v in cur_line_split][1:]

                last_linkid = None
                continue

    print("Tracked {0} of {1}.".format(len(return_dict.keys()), num_links))
    return return_dict


def read_lengths(links_length_fpath, csv_separator=",", ignore_header=True):
    """

    :param links_length_fpath:
    :param csv_separator:
    :param ignore_header:
    :return:
    """

    return_dict = {}
    with open(links_length_fpath, "r+") as rfile:
        header_ignored = not ignore_header
        for cur_line in rfile:
            if not header_ignored:
                header_ignored = True
                continue
            cur_line_split = cur_line.split(csv_separator)
            return_dict[int(cur_line_split[0])] = float(cur_line_split[1])
    return return_dict


def export_links_classification(links_class_dict, csv_file_path):
    """
    Writes a csv file with relaionship link_id -> classification
    :param links_class_dict:
    :param csv_file_path:
    :return:
    """

    with open(csv_file_path, "w+") as w_file:
        for cur_link_id, cur_class in links_class_dict.items():
            w_file.write(str(cur_link_id))
            w_file.write(",")
            w_file.write(str(cur_class))
            w_file.write("\n")

    print("Wrote file '{0}'.".format(csv_file_path))


def get_bar_color(the_key):
    """

    :param the_key:
    :return:
    """
    keys = ["D-Group 0", "D-Group 1", "D-Group 2", "D-Group 3", "D-Group 4"]
    colors = ["#FF0000", "#AA22AA", "#0000FF", "#22AAAA", "#00FF00"]
    miss_color = "#787878"

    if the_key in keys:
        return colors[keys.index(the_key)]
    else:
        return miss_color


def get_color_dict(rain=False):
    if not rain:
        return {"D-Group 0": "#FF0000",
                "D-Group 1": "#AA22AA",
                "D-Group 2": "#0000FF",
                "D-Group 3": "#22AAAA",
                "D-Group 4": "#00FF00"}
    else:
        return {"D-Group 0 Old": "#FF0000",
                "D-Group 1 Old": "#AA22AA",
                "D-Group 2 Old": "#0000FF",
                "D-Group 3 Old": "#22AAAA",
                "D-Group 4 Old": "#00FF00",
                "D-Group 0 New": "#FF7777",
                "D-Group 1 New": "#CC99CC",
                "D-Group 2 New": "#7777FF",
                "D-Group 3 New": "#99CCCC",
                "D-Group 4 New": "#77FF77"}

def plot_it(input_hydr_file_path, input_rvr_file_path, input_links_length_file_path, output_file_path, stack_bar=True,
            line_graph=True, y_lim=None):
    """

    :param input_hydr_file_path:
    :param input_rvr_file_path:
    :param input_links_length_file_path:
    :param output_file_path:
    :return:
    """

    # basic check and open/read file hydro file
    if not os.path.exists(input_hydr_file_path):
        print("File '{0}' does not exist.".format(input_hydr_file_path))
        return False
    with open(input_hydr_file_path, 'rb') as rfile:
        data_dict = pickle.load(rfile)
    print("Gotten {0} timestasmps from file {1}.".format(len(data_dict.keys()), input_hydr_file_path))

    # basic check and open/read topology file
    if not os.path.exists(input_rvr_file_path):
        print("File '{0}' does not exist.".format(input_rvr_file_path))
        return False
    topo_data = read_topo(input_rvr_file_path)

    # basic check and open/read links length file
    if not os.path.exists(input_links_length_file_path):
        print("File '{0}' does not exist.".format(input_links_length_file_path))
        return False
    link_lengths = read_lengths(input_links_length_file_path)

    # basic check - some info
    if data_dict is None:
        print("Some problem reading '{0}'.".format(input_hydr_file_path))
        return False
    if len(data_dict.keys()) == 0:
        print("Not enough info in '{0}'.".format(input_hydr_file_path))
        return False

    # extract all timestamps and link id
    all_timestamps = sorted(list(data_dict.keys()))
    if "outlet_link_id" not in data_dict[all_timestamps[0]]:
        print("Missing 'outlet_link_id' in data file.")
        return False
    outlet_linkid = data_dict[all_timestamps[0]]["outlet_link_id"]

    # define distances from all links to outlet and set up classes for links
    links_dist = DistancesDefiner.calculate_links_distances(outlet_linkid, topo_data, link_lengths)
    links_classes = DistancesDefiner.classify_links(links_dist)

    #
    links_widths = DistancesDefiner.calculate_links_width_func(outlet_linkid, topo_data)
    print("   DICT WIDTH: {0}.".format(len(links_widths.keys())))
    links_classes_width = DistancesDefiner.classify_links_width(links_widths)

    # debug
    last_timestamp = all_timestamps[-1]
    print("Last state in outlet link {0} : {1}.".format(outlet_linkid, data_dict[last_timestamp]))
    for cur_class in range(1, 6):
        counter = 0
        for cur_class_dict in list(links_classes.values()):
            if cur_class == cur_class_dict:
                counter += 1
        print("...for class {0} : {1} links.".format(cur_class, counter))

    # debug
    print("So far: {0} links dist, {1} links length, {2} links class.".format(len(links_dist), len(topo_data),
                                                                              len(links_classes)))

    #
    plots_title_frame = "Cedar River (Osage) - {0}"
    colors_dict = get_color_dict(rain=True)

    # plot hydrograph by dist
    hydr_dist_file_path = output_file_path.replace(".png", "_hydrdist.png")
    hydr_dist_plot_title = plots_title_frame.format("Hydrograph Dist.")
    print("Plotting collored hydrograph.")
    GraphsPlotter.plot_colored_hydrograph_rain(data_dict, links_classes, hydr_dist_file_path, hydr_dist_plot_title,
                                               colors_dict, class_names_frame="D-Group {0}", total_classes=5,
                                               y_lim=y_lim)

    # plot width function
    GraphsPlotter.plot_width_func(links_widths, output_file_path.replace(".png", "_widthfunc_mono.png"))
    GraphsPlotter.plot_width_func(links_widths, output_file_path.replace(".png", "_widthfunc_mult.png"),
                                  color_dict=colors_dict, width_class=links_classes_width, rain=True)

    # plot hydrograph by width
    hydr_width_file_path = output_file_path.replace(".png", "_hydrwidth.png")
    hydr_width_plot_title = plots_title_frame.format("Hydrograph Width")
    GraphsPlotter.plot_colored_hydrograph_rain(data_dict, links_classes_width, hydr_width_file_path,
                                               hydr_width_plot_title, colors_dict, class_names_frame="D-Group {0}",
                                               y_lim=y_lim)
    # plot_colored_hydrograph(data_dict, links_classes_width, output_file_path)

    # save classifications
    export_links_classification(links_classes, output_file_path.replace(".png", "_links_distclass.csv"))
    export_links_classification(links_classes_width, output_file_path.replace(".png", "_links_widthclass.csv"))

    return True


if plot_it(input_hdict_fpath_arg, input_rvr_fpath_arg, links_length_file_path, output_hpict_fpath_arg,
           y_lim=y_limit_arg):
    print("Done creating '{0}'.".format(output_hpict_fpath_arg))
else:
    print("Execution failed.")
