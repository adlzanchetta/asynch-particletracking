import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import datetime


class GraphsPlotter:

    @staticmethod
    def plot_width_func(all_links_width, output_file_path, color_dict=None, width_class=None, rain=False):
        """

        :param all_links_width:
        :param output_file_path:
        :param color_dict:
        :param width_class:
        :return:
        """

        # start stuff
        fig = plt.figure()
        ax = fig.gca()

        if (color_dict is None) or (width_class is None):
            # plot mono color
            all_widths = list(all_links_width.values())
            num_buckets = max(all_widths) - min(all_widths)
            plt.hist(all_widths, num_buckets, facecolor='grey', alpha=1.0)
        else:
            # plot classes colors

            # aggregate it
            all_classes = {}
            for cur_linkid, cur_width in all_links_width.items():
                cur_class = width_class[cur_linkid]
                if cur_class not in all_classes.keys():
                    all_classes[cur_class] = []
                all_classes[cur_class].append(cur_width)

            # plot it

            for cur_class in sorted(all_classes.keys()):
                cur_widths = all_classes[cur_class]
                cur_num_buckets = (max(cur_widths) - min(cur_widths)) + 1
                if not rain:
                    cur_color = color_dict["D-Group {0}".format(cur_class - 1)]
                else:
                    if cur_class < 0:
                        continue
                    else:
                        cur_color = color_dict["D-Group {0} Old".format(cur_class - 1)]
                plt.hist(cur_widths, cur_num_buckets, facecolor=cur_color, alpha=1.0)

        # add graph decorations
        plt.title('Station: Cedar River near Osage')
        plt.ylabel('Quantity')
        plt.xlabel('Width')
        fig.savefig(output_file_path)

        # farewell
        print("Created file '{0}'.".format(output_file_path))
        return

    @staticmethod
    def plot_colored_hydrograph(raw_data, links_classes, output_file_path, plot_title, class_color_dict,
                                class_names_frame="D-Group {0}", total_classes=5, y_lim=None):
        """

        :param raw_data:
        :param links_classes:
        :param output_file_path:
        :param plot_title:
        :param class_color_dict:
        :param class_names_frame:
        :param total_classes:
        :param y_lim:
        :return:
        """

        # change data format for a better one
        conveted_data = GraphsPlotter._convert_data(raw_data, links_classes)
        all_timestamps = sorted(list(raw_data.keys()))

        #
        first_key = list(conveted_data.keys())[0]
        num_x_values = len(conveted_data[first_key])

        fig = plt.figure()

        # ### hydrograph

        plt.subplot(121)
        ax = fig.gca()

        # plot bar
        width = 1
        x_vals = np.arange(num_x_values)
        leg_refs = []
        leg_vals = []
        prev_bottom = np.zeros(num_x_values)
        for cur_class in sorted(list(conveted_data.keys())):
            '''
            cur_bar = ax.bar(x_vals, conveted_data[cur_class], width, bottom=prev_bottom, color=get_bar_color(cur_class),
                             edgecolor="none")
            '''
            cur_bar = ax.bar(x_vals, conveted_data[cur_class], width, bottom=prev_bottom,
                             color=class_color_dict[cur_class], edgecolor="none")
            leg_refs.append(cur_bar)
            leg_vals.append(cur_class)
            prev_bottom = prev_bottom + conveted_data[cur_class]

        # define ylim and xlim
        num_x = len(conveted_data[list(conveted_data.keys())[0]])
        max_y = 0
        peak_x = 0
        for cur_x in range(num_x):
            cur_sum = 0
            for cur_key in list(conveted_data.keys()):
                cur_sum += conveted_data[cur_key][cur_x]
            if cur_sum > max_y:
                max_y = cur_sum
                peak_x = cur_x
        print("Max y: {0}.".format(max_y))
        max_y = int(np.ceil(max_y * 1.1))
        print(" rounded to: {0}.".format(max_y))

        # fill holes
        the_disch = []
        for cur_x in range(len(x_vals)):
            if prev_bottom[cur_x] != 0:
                the_disch.append(prev_bottom[cur_x])
            else:
                the_disch.append(raw_data[all_timestamps[cur_x]]["discharge"])

        # plot line
        ax.plot(x_vals + 0.5, the_disch, linewidth=2, color="#000000")
        plt.axvline(x=peak_x, color='w', alpha=0.5)

        # define all ticks
        all_ticks = ["" for i in all_timestamps]
        all_ticks[0] = datetime.datetime.fromtimestamp(all_timestamps[0]).strftime('%d/%m/%Y %H:%M')
        all_ticks[-1] = datetime.datetime.fromtimestamp(all_timestamps[-1]).strftime('%d/%m/%Y %H:%M')
        all_ticks[peak_x] = datetime.datetime.fromtimestamp(all_timestamps[peak_x]).strftime('%d/%m/%Y %H:%M')
        print("Timestamps: {0} from {1} to {2}.".format(len(all_timestamps), all_timestamps[0], all_timestamps[-1]))

        # titles
        plt.title(plot_title)
        plt.ylabel('Discharge [cm/s]')
        plt.xlabel('Time')
        if y_lim is None:
            plt.ylim([0, max_y])
        else:
            plt.ylim([0, y_lim])
        plt.xlim([0, num_x])
        plt.legend(leg_refs, leg_vals, loc='upper right')
        plt.xticks(x_vals, all_ticks)

        # ### pie plot
        plt.subplot(122)

        # get peak sample, removing empties
        pie_sizes = []
        pie_labels = []
        pie_colors = []
        for cur_class in sorted(list(conveted_data.keys())):
            if conveted_data[cur_class][peak_x] == 0:
                continue
            pie_sizes.append(conveted_data[cur_class][peak_x])
            pie_labels.append(cur_class)
            pie_colors.append(class_color_dict[cur_class])

        # get plot elements
        plt.pie(pie_sizes, labels=pie_labels, colors=pie_colors)
        plt.axis('equal')

        # ### save image file
        fig.set_size_inches(15, 5)
        fig.savefig(output_file_path)
        print("Plotted file {0}.".format(output_file_path))

    @staticmethod
    def plot_colored_hydrograph_rain(raw_data, links_classes, output_file_path, plot_title, class_color_dict,
                                     class_names_frame="D-Group {0}", total_classes=5, y_lim=None):
        """

        :param raw_data:
        :param links_classes:
        :param output_file_path:
        :param plot_title:
        :param class_color_dict:
        :param class_names_frame:
        :param total_classes:
        :param y_lim:
        :return:
        """

        # change data format for a better one
        print("Converting data with rain.")
        conveted_data = GraphsPlotter._convert_data(raw_data, links_classes, rain=True)
        all_timestamps = sorted(list(raw_data.keys()))

        #
        first_key = list(conveted_data.keys())[0]
        num_x_values = len(conveted_data[first_key])

        fig = plt.figure()

        # ### hydrograph

        plt.subplot(121)
        ax = fig.gca()

        # plot bar
        width = 1
        x_vals = np.arange(num_x_values)
        leg_refs = []
        leg_vals = []
        prev_bottom = np.zeros(num_x_values)

        # plot bars
        for cur_class_count in range(len(conveted_data.keys())):
            rest_div = cur_class_count % 2
            valu_div = int(cur_class_count / 2)
            data_age = "Old" if rest_div == 0 else "New"
            cur_class = "D-Group {0} {1}".format(valu_div, data_age)

            print("Adding plot {0}...".format(cur_class))

            cur_bar = ax.bar(x_vals, conveted_data[cur_class], width, bottom=prev_bottom,
                             color=class_color_dict[cur_class], edgecolor="none")
            leg_refs.append(cur_bar)
            leg_vals.append(cur_class)
            prev_bottom = prev_bottom + conveted_data[cur_class]

        # define ylim and xlim
        num_x = len(conveted_data[list(conveted_data.keys())[0]])
        max_y = 0
        peak_x = 0
        for cur_x in range(num_x):
            cur_sum = 0
            for cur_key in list(conveted_data.keys()):
                cur_sum += conveted_data[cur_key][cur_x]
            if cur_sum > max_y:
                max_y = cur_sum
                peak_x = cur_x
        print("Max y: {0}.".format(max_y))
        max_y = int(np.ceil(max_y * 1.1))
        print(" rounded to: {0}.".format(max_y))

        # fill holes
        the_disch = []
        for cur_x in range(len(x_vals)):
            if prev_bottom[cur_x] != 0:
                the_disch.append(prev_bottom[cur_x])
            else:
                the_disch.append(raw_data[all_timestamps[cur_x]]["discharge"])

        # plot line
        ax.plot(x_vals + 0.5, the_disch, linewidth=2, color="#000000")
        plt.axvline(x=peak_x, color='w', alpha=0.5)

        # define all ticks
        all_ticks = ["" for i in all_timestamps]
        all_ticks[0] = datetime.datetime.fromtimestamp(all_timestamps[0]).strftime('%d/%m/%Y %H:%M')
        all_ticks[-1] = datetime.datetime.fromtimestamp(all_timestamps[-1]).strftime('%d/%m/%Y %H:%M')
        all_ticks[peak_x] = datetime.datetime.fromtimestamp(all_timestamps[peak_x]).strftime('%d/%m/%Y %H:%M')
        print("Timestamps: {0} from {1} to {2}.".format(len(all_timestamps), all_timestamps[0], all_timestamps[-1]))

        # titles
        plt.title(plot_title)
        plt.ylabel('Discharge [cm/s]')
        plt.xlabel('Time')
        if y_lim is None:
            plt.ylim([0, max_y])
        else:
            plt.ylim([0, y_lim])
        plt.xlim([0, num_x])
        plt.legend(leg_refs, leg_vals, loc='upper right')
        plt.xticks(x_vals, all_ticks)

        # ### pie plot
        plt.subplot(122)

        # get peak sample, removing empties
        pie_sizes = []
        pie_labels = []
        pie_colors = []
        for cur_class in sorted(list(conveted_data.keys())):
            if conveted_data[cur_class][peak_x] == 0:
                continue
            pie_sizes.append(conveted_data[cur_class][peak_x])
            pie_labels.append(cur_class)
            pie_colors.append(class_color_dict[cur_class])

        # get plot elements
        plt.pie(pie_sizes, labels=pie_labels, colors=pie_colors)
        plt.axis('equal')

        # ### save image file
        fig.set_size_inches(15, 5)
        fig.savefig(output_file_path)
        print("Plotted file {0}.".format(output_file_path))

    @staticmethod
    def _convert_data(raw_data, links_classes, total_classes=5, rain=False):
        """
        Convert particle counting data into classes partial discharge data
        :param raw_data:
        :param links_classes:
        :param total_classes:
        :return: Dictionary with format {"D-Group 0":[12, 10, ...], "D-Group 1":[12, 10, ...]}
        """

        # set up return dictionary
        ret_dict = {}
        if rain:
            for cur_class in range(total_classes):
                ret_dict["D-Group {0} Old".format(cur_class)] = []
                ret_dict["D-Group {0} New".format(cur_class)] = []
        else:
            for cur_class in range(total_classes):
                ret_dict["D-Group {0}".format(cur_class)] = []

        # fill it
        for cur_timestamp in sorted(raw_data.keys()):
            cur_dict = raw_data[cur_timestamp]
            cur_total_disch = cur_dict['discharge']

            # get sum of particles
            cur_total_parts = 0
            for cur_key in cur_dict.keys():
                try:
                    cur_link_id = int(cur_key)
                    if not rain:
                        cur_total_parts += cur_dict[cur_link_id]
                    else:
                        for cur_source_count in cur_dict[cur_link_id].values():
                            cur_total_parts += cur_source_count
                    continue

                except ValueError:
                    continue

            # build temporary dict
            cur_tmp_dict = {}
            for cur_class in range(1, total_classes+1):
                if rain:
                    cur_tmp_dict[cur_class] = 0
                    cur_tmp_dict[cur_class * (-1)] = 0
                else:
                    cur_tmp_dict[cur_class] = 0

            # build partition
            for cur_key in cur_dict.keys():
                try:
                    cur_link_id = int(cur_key)
                    cur_dist_clas = links_classes[cur_link_id]

                    if rain:
                        cur_parts_old = 0
                        cur_parts_new = 0
                        for cur_source in cur_dict[cur_link_id].keys():
                            if cur_source < 0:
                                cur_parts_old += cur_dict[cur_link_id][cur_source]
                            else:
                                cur_parts_new += cur_dict[cur_link_id][cur_source]
                        cur_part_old_disch = cur_total_disch * (cur_parts_old / cur_total_parts)
                        cur_part_new_disch = cur_total_disch * (cur_parts_new / cur_total_parts)
                        cur_tmp_dict[cur_dist_clas * (-1)] += cur_part_old_disch
                        cur_tmp_dict[cur_dist_clas] += cur_part_new_disch
                    else:
                        cur_parts = cur_dict[cur_link_id]
                        cur_part_disch = cur_total_disch * (cur_parts / cur_total_parts)
                        cur_tmp_dict[cur_dist_clas] += cur_part_disch

                    continue

                except ValueError:
                    continue

            # transfer from cur dict to permanent dict
            for cur_class in range(total_classes):
                if rain:
                    ret_dict["D-Group {0} Old".format(cur_class)].append(cur_tmp_dict[(cur_class + 1) * (-1)])
                    ret_dict["D-Group {0} New".format(cur_class)].append(cur_tmp_dict[cur_class + 1])
                else:
                    ret_dict["D-Group {0}".format(cur_class)].append(cur_tmp_dict[cur_class + 1])

        return ret_dict

    def __init__(self):
        return