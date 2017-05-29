import numpy as np


# Static Class - Library of functions (its methods) for dealing with distances
class DistancesDefiner:

    @staticmethod
    def calculate_links_distances(outlet_linkid, dict_topo, dict_lengths):
        """

        :param outlet_linkid:
        :param dict_topo:
        :param dict_lengths:
        :return: Dictionary with the distances of each link id to the outlet of the watershed
        """

        # basic check
        if outlet_linkid is None:
            print("Invalid outlet link id: {0}.".format(outlet_linkid))
            return None
        elif outlet_linkid not in dict_lengths.keys():
            print("Outlet link id not found in lengths list: {0}.".format(outlet_linkid))
            return None
        elif outlet_linkid not in dict_topo.keys():
            print("Outlet link id not found in topology list: {0}.".format(outlet_linkid))
            return None

        print(
        "Starting at {0} -> {1} ({2}).".format(outlet_linkid, dict_topo[outlet_linkid], dict_lengths[outlet_linkid]))

        dict_cumm = {}
        DistancesDefiner._set_cumulative_distance(outlet_linkid, 0, dict_topo, dict_lengths, dict_cumm)

        print("Defined cumulative distances for {0} links.".format(len(dict_cumm.keys())))
        max_key = None
        max_dist = 0
        for cur_key in dict_cumm.keys():
            cur_dist = dict_cumm[cur_key]
            if cur_dist > max_dist:
                max_dist = cur_dist
                max_key = cur_key
        print("Maximum distance is {0}km ({1}).".format(max_dist, max_key))

        return dict_cumm

    @staticmethod
    def classify_links(links_dist_dict, num_classes=5):
        """

        The lower the class, the closer to the outlet
        :param links_dist_dict:
        :param num_classes:
        :return: A dictionary link_id -> class
        """

        # define thresholds
        all_dists = sorted(links_dist_dict.values())
        links_interval = int(len(all_dists) / num_classes)
        thresholds = []
        count_classes = 1
        while count_classes < num_classes:
            cur_idx = count_classes * links_interval
            thresholds.append(all_dists[cur_idx])
            count_classes += 1

        # build return dictionary
        ret_dict = {}
        for cur_link_id in list(links_dist_dict.keys()):
            cur_dist = links_dist_dict[cur_link_id]
            cur_pot_class = 1
            while cur_pot_class < num_classes:
                if cur_dist < thresholds[cur_pot_class-1]:
                    ret_dict[cur_link_id] = cur_pot_class
                    break
                cur_pot_class += 1
            if cur_pot_class == num_classes:
                ret_dict[cur_link_id] = cur_pot_class

        return ret_dict

    @staticmethod
    def calculate_links_width_func(outlet_linkid, dict_topo):
        """

        :param outlet_linkid:
        :param dict_topo:
        :return:
        """

        # basic check
        if outlet_linkid is None:
            print("Invalid outlet link id: {0}.".format(outlet_linkid))
            return None
        elif outlet_linkid not in dict_topo.keys():
            print("Outlet link id not found in topology list: {0}.".format(outlet_linkid))
            return None

        dict_width = {}
        DistancesDefiner._set_cumulative_width(outlet_linkid, 1, dict_topo, dict_width)

        print("Defined width funcs. for {0} links.".format(len(dict_width.keys())))
        max_key = None
        max_width = 0
        for cur_key in dict_width.keys():
            cur_width = dict_width[cur_key]
            if cur_width > max_width:
                max_width = cur_width
                max_key = cur_key
        print("Maximum width is {0} ({1}).".format(max_width, max_key))

        return dict_width

    @staticmethod
    def classify_links_width(dict_width, num_classes=5):
        """

        :param dict_width:
        :return:
        """

        # invert dictionary
        inverted_dict = {}
        for key, value in dict_width.items():
            if value not in inverted_dict.keys():
                inverted_dict[value] = []
            inverted_dict[value].append(key)

        # define links per class
        total_links = len(dict_width.keys())
        links_per_group = int(np.ceil(total_links/num_classes))

        # iterates, grouping
        ret_dict = {}
        cur_group = 1
        count_added = 0
        for cur_width in sorted(inverted_dict.keys()):
            if count_added > (cur_group * links_per_group):
                cur_group += 1
            for cur_link_id in inverted_dict[cur_width]:
                ret_dict[cur_link_id] = cur_group
            count_added += len(inverted_dict[cur_width])

        # debug
        debug_dict = {}
        for cur_group, value in ret_dict.items():
            if value not in debug_dict:
                debug_dict[value] = 0
            debug_dict[value] += 1
        print("Dict. widths debug: {0}.".format(debug_dict))
        print("Dict. widths has: {0} keys.".format(len(ret_dict.keys())))

        return ret_dict


    @staticmethod
    def _set_cumulative_width(parent_link_id, cur_width, dict_topo, dict_width):
        """

        :param parent_link_id:
        :param dict_topo:
        :param dict_width:
        :return:
        """

        cur_link_accum = 1 + cur_width
        dict_width[parent_link_id] = cur_link_accum
        print("Width for {0} : {1}.".format(parent_link_id, cur_link_accum))
        if dict_topo[parent_link_id] is None:
            return
        for cur_par_link_id in dict_topo[parent_link_id]:
            DistancesDefiner._set_cumulative_width(cur_par_link_id, cur_link_accum, dict_topo, dict_width)
        return

    @staticmethod
    def _set_cumulative_distance(parent_link_id, dist_accumulated, topo_dict, leng_dict, cumulative_dict):
        """

        :param dist_accumulated:
        :param topo_dict:
        :param leng_dict:
        :param cumulative_dict:
        :return:
        """
        cur_link_length = leng_dict[parent_link_id]
        cur_link_accum = cur_link_length + dist_accumulated
        cumulative_dict[parent_link_id] = cur_link_accum
        if topo_dict[parent_link_id] is None:
            return
        for cur_par_link_id in topo_dict[parent_link_id]:
            DistancesDefiner._set_cumulative_distance(cur_par_link_id, cur_link_accum, topo_dict, leng_dict,
                                                      cumulative_dict)
        return

    def __init__(self):
        return
