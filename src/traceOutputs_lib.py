import numpy as np
import datetime
import _thread
import h5py
import math
import os


# Static Class - holds all global constant values for the program
class GblVars:
    vh = 0.02
    ki = 0.02
    k3 = 0.0000020425
    a = 0
    b = 99.0
    sl = 0.1
    alpha = 3.0
    lambda_1 = 0.2
    lambda_2 = -0.1
    vel_ref = 0.33
    delta_t = 600                 # assuming 10 minutes time interval (60 secs * 10 min)
    domain_structure = {}         # expected to be a dictionary of [link_id]->HillslopeLinkPrm

    vol_particles = 0             # volume of water that represents a particle

    def __init__(self):
        return


# Dynamic Class - holds permanent parameters and topological-related constant values of a hillslope
class HillslopeLinkPrm:
    id = None                     # hl-id
    upstream_hl_ids = None        # list of hl's draining into the current link
    downstream_hl_id = None       #
    channel_storage = None        #
    upstream_area = None          #
    hillslope_area = None         #
    link_length = None            #

    def __init__(self, id):
        self._id = id
        self.upstream_hl_ids = []

    def add_upstream_hl_id(self, hl_id):
        if hl_id not in self.upstream_hl_ids:
            self.upstream_hl_ids.append(hl_id)

    def set_downstream_hl_id(self, hl_id):
        self.downstream_hl_id = hl_id

    def set_attributes(self, upstream_area, hillslope_area, link_length):
        self.upstream_area = upstream_area
        self.hillslope_area = hillslope_area
        self.link_length = link_length

    def get_upstream_area(self):
        return self.upstream_area

    def get_hillslope_area(self):
        return self.hillslope_area

    def get_link_length(self):
        return self.link_length

    def get_downstream_hl_id(self):
        return self.downstream_hl_id


# Dynamic Class - The snapshot of the system at a specific moment in time
class DomainSnapshot:
    timestamp = None
    hl_states = None
    outlet_link_id = None
    hl_cummulative_rained_parts = None

    def count_particles(self):
        """

        :return:
        """
        counting = 0
        for cur_link_id in self.hl_states.keys():
            counting += self.hl_states[cur_link_id].count_particles()
        return counting

    def count_particles_by_layer_source(self, aggregate_rain=True):
        """

        :param aggregate_rain: If True, all rain-generated particles are aggregated into a single source numbered '1'
        :return: Integer of counting and Dictionary of [layer_source_flag]:[]
        """

        # create basic dictionary
        return_dict = {
            ParticleManager.LAYER_POND: 0,
            ParticleManager.LAYER_TOPLAYER: 0,
            ParticleManager.LAYER_SUBSURFACE: 0,
            ParticleManager.LAYER_CHANNEL: 0
        }

        # create aggregated rain index if necessary
        if aggregate_rain:
            return_dict[ParticleManager.LAYER_RAIN] = 0

        counting = 0
        for cur_hl_state in self.hl_states.values():
            # count from ponds
            tmp_count = cur_hl_state.count_particles_from(ParticleManager.LAYER_POND)
            return_dict[ParticleManager.LAYER_POND] += tmp_count
            counting += tmp_count

            # count from top layer
            tmp_count = cur_hl_state.count_particles_from(ParticleManager.LAYER_TOPLAYER)
            return_dict[ParticleManager.LAYER_TOPLAYER] += tmp_count
            counting += tmp_count

            # count from subsurface
            tmp_count = cur_hl_state.count_particles_from(ParticleManager.LAYER_SUBSURFACE)
            return_dict[ParticleManager.LAYER_SUBSURFACE] += tmp_count
            counting += tmp_count

            # count from channel
            tmp_count = cur_hl_state.count_particles_from(ParticleManager.LAYER_CHANNEL)
            return_dict[ParticleManager.LAYER_CHANNEL] += tmp_count
            counting += tmp_count

            # count from rainfall
            if aggregate_rain:
                tmp_count = cur_hl_state.count_particles_from(ParticleManager.LAYER_RAIN)
                return_dict[ParticleManager.LAYER_RAIN] += tmp_count
                counting += tmp_count

        return counting, return_dict

    def inherit_cummulated_rained_parts(self, previous_domain_snapshot):
        """
        Copies the dictionary of accumulated rained particles from a given snapshot into the current object
        :param previous_domain_snapshot:
        :return:
        """

        for cur_linkid, cur_parts_count in previous_domain_snapshot.hl_cummulative_rained_parts.items():
            self.hl_cummulative_rained_parts[cur_linkid] = cur_parts_count
            '''
            if cur_linkid == 522792:
                print("Inheriting {0} rain particles counting on link {1}.".format(cur_parts_count, cur_linkid))
            '''

    def add_particles_from_rainfall(self, cur_link_id, cur_acc_rain_wc):
        """

        :param cur_link_id:
        :param cur_acc_rain_wc:
        :return:
        """

        # basic checl to avoid zero-division
        if GblVars.vol_particles == 0:
            return

        # estimate the number of particles to be added from rainfall
        acc_vol_water = cur_acc_rain_wc * GblVars.domain_structure[cur_link_id].upstream_area * (10**6)  # km2 to m2
        expected_acc_rain_particles = int(np.floor(acc_vol_water / GblVars.vol_particles))
        if cur_link_id not in self.hl_cummulative_rained_parts:
            self.hl_cummulative_rained_parts[cur_link_id] = 0
        generated_acc_rain_particles = self.hl_cummulative_rained_parts[cur_link_id]
        particles_to_be_generated = expected_acc_rain_particles - generated_acc_rain_particles

        if cur_link_id == 522792:
            print("In link {0}: will generate {1} particles ({2} - {3}).".format(cur_link_id, particles_to_be_generated,
                                                                                 expected_acc_rain_particles,
                                                                                 generated_acc_rain_particles))

        # create and add the particles
        for count_generated in range(particles_to_be_generated):
            cur_new_part = Particle(cur_link_id, self.timestamp)
            self.hl_states[cur_link_id].parts_pond_frnt.append(cur_new_part)
            self.hl_cummulative_rained_parts[cur_link_id] += 1

    def get_contributing_links(self, aggregate_rain=True):
        """

        :param aggregate_rain:
        :return: A dictionary of link_id -> number of particles
        """

        # basic test
        if self.outlet_link_id is None:
            print("Got None dict for contrib. links - No outled link id.")
            return None
        elif self.outlet_link_id not in self.hl_states.keys():
            print("Got None dict for contrib. links - Missing outled link id.")
            return None

        # gets the hillslope-link state of the outlet
        cur_state = self.hl_states[self.outlet_link_id]
        links_id = {}
        links_id["discharge"] = cur_state.disch_chnl
        links_id["outlet_link_id"] = self.outlet_link_id

        #
        for cur_particle in cur_state.parts_chnl_frnt:
            cur_link_id = cur_particle.get_linkid()
            if cur_link_id not in links_id:
                links_id[cur_link_id] = {ParticleManager.LAYER_POND: 0,
                                         ParticleManager.LAYER_TOPLAYER: 0,
                                         ParticleManager.LAYER_SUBSURFACE: 0,
                                         ParticleManager.LAYER_CHANNEL: 0}
                if aggregate_rain:
                    links_id[cur_link_id][ParticleManager.LAYER_RAIN] = 0

            #
            cur_p_source = cur_particle.get_layer_source()
            if cur_p_source < 0:
                links_id[cur_link_id][cur_p_source] += 1
            elif aggregate_rain:
                links_id[cur_link_id][ParticleManager.LAYER_RAIN] += 1
            else:
                if cur_p_source not in links_id[cur_link_id].keys():
                    links_id[cur_link_id][cur_p_source] = 0
                links_id[cur_link_id][cur_p_source] += 1

        return links_id

    def set_timestamp(self, the_timestamp):
        """

        :param the_timestamp:
        :return:
        """
        self.timestamp = the_timestamp

    def __init__(self, hillslopelink_ids=None, the_timestamp=None):
        # start it
        self.hl_states = {}
        self.timestamp = the_timestamp
        self.hl_cummulative_rained_parts = {}

        # initializes each
        if hillslopelink_ids is not None:
            for cur_hl_id in hillslopelink_ids:
                self.hl_states[cur_hl_id] = HillslopeLinkState()


# Dynamic Class - The state of a hillslope-link pair in a moment of time
class HillslopeLinkState:
    parts_chnl_frnt = None        # list of Particle objects in the front part of the channel
    parts_pond_frnt = None        # list of Particle objects in the back part of the channel
    parts_topl_frnt = None        # list of Particle objects in the back part of the channel
    parts_subs_frnt = None        # list of Particle objects in the back part of the channel
    disch_chnl = None             # discharge channel                 (m3/s)
    disch_pdch = None             # discharge ponds -> channel        (m3/s)
    disch_pdtl = None             # discharge ponds -> top layer      (m3/s)
    disch_tlss = None             # discharge top layer -> subsurface (m3/s)
    disch_ssch = None             # discharge subsurface -> channel   (m3/s)
    volum_chnl = None             # volume of water in channel
    volum_pond = None             # volume of water in ponds
    volum_tplr = None             # volume of water in top layer
    volum_subs = None             # volume of water in subsurface

    def count_particles(self, in_channel=True, in_ponds=True, in_toplayer=True, in_subsurface=True):
        """

        :param in_channel:
        :param in_ponds:
        :param in_toplayer:
        :param in_subsurface:
        :return:
        """
        ret_count = 0
        ret_count = ret_count + len(self.parts_chnl_frnt) if in_channel else ret_count
        ret_count = ret_count + len(self.parts_pond_frnt) if in_ponds else ret_count
        ret_count = ret_count + len(self.parts_topl_frnt) if in_toplayer else ret_count
        ret_count = ret_count + len(self.parts_subs_frnt) if in_subsurface else ret_count
        return ret_count

    def count_particles_from(self, layer_source):
        """

        :param layer_source:
        :return:
        """

        ret_count = 0
        all_parts = self.parts_chnl_frnt + self.parts_pond_frnt + self.parts_topl_frnt + self.parts_subs_frnt

        # get from specific layer
        if layer_source != ParticleManager.LAYER_RAIN:
            for cur_part in all_parts:
                if cur_part.get_layer_source() == layer_source:
                    ret_count += 1
            return ret_count

        # get from any positive number (sourcered by rainfall)
        if layer_source == ParticleManager.LAYER_RAIN:
            for cur_part in all_parts:
                if cur_part.get_layer_source() > 0:
                    ret_count += 1
            return ret_count

        return None

    def set_dischs_and_volume(self, link_id, disch_chnl, wc_pond, wc_topl, wc_subs):
        """

        :param link_id:
        :param disch_chnl:
        :param wc_pond: Water Column stored in ponds (in meters)
        :param wc_topl: Water Column stored in top layer (in meters)
        :param wc_subs: Water Column stored in sub surface (in meters)
        :return:
        """

        k2 = GblVars.vh * (GblVars.domain_structure[link_id].link_length/GblVars.domain_structure[link_id].hillslope_area) * 60 * 0.001
        kt = k2*(GblVars.a + (GblVars.b * ((1 - (wc_pond / GblVars.sl))**GblVars.alpha)))

        # solve channel
        # print("Set channel discharge ({0}).".format(disch_chnl))
        self.disch_chnl = disch_chnl
        self.volum_chnl = self.__calculate_channel_volume(link_id)

        # solve pond
        self.volum_pond = HillslopeLinkState.__calculate_volume_from_water_column(link_id, wc_pond)
        self.disch_pdch = k2 * self.volum_pond
        self.disch_pdtl = kt * self.volum_pond

        # solve top layer
        self.volum_tplr = HillslopeLinkState.__calculate_volume_from_water_column(link_id, wc_topl)
        self.disch_tlss = GblVars.ki * self.volum_tplr

        # solve sub-surface
        self.volum_subs = HillslopeLinkState.__calculate_volume_from_water_column(link_id, wc_subs)
        self.disch_ssch = GblVars.k3 * self.volum_subs

    def __calculate_channel_volume(self, link_id):
        """

        :param link_id:
        :return:
        """
        chan_len = GblVars.domain_structure[link_id].get_link_length()
        chan_aup = GblVars.domain_structure[link_id].get_upstream_area()
        chan_ahl = GblVars.domain_structure[link_id].get_hillslope_area()
        chan_dsc = self.disch_chnl

        # print("Link length: {0}".format(chan_len))

        tau = ((1 - GblVars.lambda_1) * chan_len * 1000)/(GblVars.vel_ref * (chan_aup**GblVars.lambda_2))
        vol_disch = tau * ((chan_dsc**(1 - GblVars.lambda_1))/(1 - GblVars.lambda_1))

        return vol_disch

    @staticmethod
    def __calculate_volume_from_water_column(link_id, water_column):
        """

        :param link_id:
        :param water_column:
        :return:
        """
        return GblVars.domain_structure[link_id].get_hillslope_area() * water_column

    def __init__(self):
        self.parts_chnl_frnt = []
        self.parts_pond_frnt = []
        self.parts_topl_frnt = []
        self.parts_subs_frnt = []


# Dynamic Class -
class Particle:
    _id = None
    _linkid_source = None
    _layer_source = None   # expected to be a value from ParticleManager.LAYER_... or a insterions timestamp

    def get_linkid(self):
        return self._linkid_source

    def get_layer_source(self):
        return self._layer_source

    def __init__(self, link_id, layer_source):
        self._id = ParticleManager.give_me_the_particle_id()
        self._linkid_source = link_id
        self._layer_source = layer_source


# Static Class - used to create particles consistently
class ParticleManager:
    LAYER_RAIN = 1
    LAYER_POND = -1
    LAYER_TOPLAYER = -2
    LAYER_SUBSURFACE = -3
    LAYER_CHANNEL = -4

    _count_particles = 0

    @staticmethod
    def give_me_the_particle_id():
        ParticleManager._count_particles += 1
        return ParticleManager._count_particles

    @staticmethod
    def particles_created():
        return ParticleManager._count_particles

    def __init__(self):
        return


# Static Class - Library of functions (its methods) for performing the tracking steps
class OutputTracer:

    @staticmethod
    def distribute_particles_proportional(first_h5_file, max_particles, outlet_link_id):
        """
        Creates a snapshot with initial particles distributed proportionally to the outlet channel discharge
        :param topo:
        :param first_h5_file:
        :param max_particles:
        :param outlet_link_id:
        :return: Initial particles dictionary
        """

        link_discharge = None
        ret_dict = {}

        print("...at '{0}'.".format(datetime.datetime.now()))

        # reading file
        print("Reading file '{0}'.".format(first_h5_file))
        disch_dict = H5FileReader.read_h5_file(first_h5_file)

        print("...at '{0}'.".format(datetime.datetime.now()))

        # find proportion particles/storage
        if max_particles is None:
            min_dich = math.inf
            min_linkid = None
            for cur_linkid in disch_dict.keys():
                if disch_dict[cur_linkid] < min_dich:
                    min_linkid, min_dich = cur_linkid, disch_dict[cur_linkid]
            vol_disch2 = OutputTracer.calculate_volume_in_link(topo, disch_dict, min_linkid)
            particle_ratio = 1 / vol_disch2
        else:
            min_dich = disch_dict[outlet_link_id]
            vol_disch2 = OutputTracer.calculate_volume_in_link(topo, min_dich, outlet_link_id)
            particle_ratio = max_particles / vol_disch2
        print("Ref. disch.: {0}, ref. volum.:{1}.".format(min_dich, vol_disch2))
        print("Part. ratio: {0}".format(particle_ratio))

        print("...at '{0}'.".format(datetime.datetime.now()))

        # distribute particles through network
        for cur_link_id in disch_dict.keys():
            cur_vol = OutputTracer.calculate_volume_in_link(topo, disch_dict, cur_link_id)
            cur_parts = int(particle_ratio * cur_vol)
            ret_dict[cur_link_id] = []
            for count_p in range(0, cur_parts):
                ret_dict[cur_link_id].append(Particle(cur_link_id))

        print("...at '{0}'.".format(datetime.datetime.now()))

        # debug
        for count_i in range(0, 5):
            cur_link_id = list(disch_dict.keys())[count_i]
            print("Link {0}: {1} ({2} m3/s).".format(cur_link_id, len(ret_dict[cur_link_id]), disch_dict[cur_link_id]))
        print("Link {0}: {1} ({2} m3/s).".format(outlet_link_id, len(ret_dict[outlet_link_id]),
                                                 disch_dict[outlet_link_id]))

        print("Created {0} particles.".format(ParticleManager.particles_created()))
        print("...at '{0}'.".format(datetime.datetime.now()))

        return ret_dict

    @staticmethod
    def distribute_particles_equally(timestamp=None, parts_in_pounds=0, parts_in_toplayer=0, parts_in_subsurface=0,
                                     parts_in_channel=0):
        """
        Creates a snapshot with initial particles distributed proportionally to the outlet channel discharge
        :param timestamp:
        :param parts_in_pounds:
        :param parts_in_toplayer:
        :param parts_in_subsurface:
        :param parts_in_channel:
        :return: A new DomainSnapshot object filled with new Particle objects
        """

        ret_obj = DomainSnapshot(the_timestamp=timestamp)

        # print("...at '{0}'.".format(datetime.datetime.now()))

        # distribute particles through network
        for cur_link_id in GblVars.domain_structure.keys():

            cur_state_obj = HillslopeLinkState()
            for i in range(0, parts_in_pounds):
                cur_state_obj.parts_pond_frnt.append(Particle(cur_link_id, ParticleManager.LAYER_POND))
            for i in range(0, parts_in_toplayer):
                cur_state_obj.parts_topl_frnt.append(Particle(cur_link_id, ParticleManager.LAYER_TOPLAYER))
            for i in range(0, parts_in_subsurface):
                cur_state_obj.parts_subs_frnt.append(Particle(cur_link_id, ParticleManager.LAYER_SUBSURFACE))
            for i in range(0, parts_in_channel):
                cur_state_obj.parts_chnl_frnt.append(Particle(cur_link_id, ParticleManager.LAYER_CHANNEL))
            ret_obj.hl_states[cur_link_id] = cur_state_obj

        return ret_obj

    @staticmethod
    def calculate_volume_in_link(topo, disch_dict, link_id):
        """

        :param topo:
        :param disch_dict:
        :param link_id:
        :return:
        """

        # print("{0} of {1} ?".format(link_id, topo[link_id]))
        chan_len = topo[link_id].get_link_length()
        chan_aup = topo[link_id].get_upstream_area()
        chan_ahl = topo[link_id].get_hillslope_area()
        chan_dsc = disch_dict[link_id]

        # print("Link length: {0}".format(chan_len))

        tau = ((1 - GblVars.lambda_1) * chan_len * 1000)/(GblVars.vel_ref * (chan_aup**GblVars.lambda_2))
        vol_disch = tau * ((chan_dsc**(1 - GblVars.lambda_1))/(1 - GblVars.lambda_1))

        return vol_disch

    def __init__(self):
        return


# Static Class - Library of functions (its methods) for reading Asynch files (.rvr, .prm, ...)
class AsynchFilesReader:

    @staticmethod
    def build_topology(rvr_fpath):
        """

        :param rvr_fpath:
        :return: Dictionary of HillslopeLinkPrm objects with link ids as keys.
        """

        # basic check
        if not os.path.exists(rvr_fpath):
            print("File not found: '{0}'.".format(rvr_fpath))
            return None

        # start variables
        counter = 0
        all_hillslopelinks = {}
        last_linkid = None

        # read it line by line
        with open(rvr_fpath, "r+") as rfile:
            num_links = None
            percent_dot = 0
            print("Building topology:")
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

                elif (len(cur_line_split) == 1) and (last_linkid is not None):
                    if last_linkid not in all_hillslopelinks.keys():
                        all_hillslopelinks[last_linkid] = HillslopeLinkPrm(last_linkid)
                    last_linkid = None
                    counter += 1

                elif (len(cur_line_split) > 1) and (last_linkid is not None):
                    # create obj if necessary
                    if last_linkid not in all_hillslopelinks.keys():
                        cur_hl = HillslopeLinkPrm(last_linkid)
                        all_hillslopelinks[last_linkid] = cur_hl
                    else:
                        cur_hl = all_hillslopelinks[last_linkid]
                    # parse line and set values to obj
                    for cur_up_hl_id in [int(s) for s in cur_line_split[1:]]:
                        cur_hl.add_upstream_hl_id(cur_up_hl_id)
                        # create parent if necessary
                        if cur_up_hl_id not in all_hillslopelinks.keys():
                            all_hillslopelinks[cur_up_hl_id] = HillslopeLinkPrm(cur_up_hl_id)
                        # set parents ref downstream
                        all_hillslopelinks[cur_up_hl_id].set_downstream_hl_id(last_linkid)
                    last_linkid = None
                    counter += 1

                # debug message
                cur_percent = counter / num_links
                if cur_percent > percent_dot:
                    print("  {0}%".format(int(percent_dot * 100)))
                    percent_dot += 0.1

        print("Created topology with {0} links.".format(len(all_hillslopelinks.keys())))
        return all_hillslopelinks

    @staticmethod
    def fill_parameters(topology, prm_fpath):
        """

        :param topology:
        :param prm_fpath:
        :return: Boolean. True if it was possible to perform the changes in 'prm_fpath' var, False otherwise
        """

        # basic checks
        if topology is None:
            print("fill_parameters: provided topology is None.")
            return False
        if prm_fpath is None:
            print("fill_parameters: provided prm file path is None.")
            return False
        if not os.path.exists(prm_fpath):
            print("fill_parameters: provided prm file ({0}) does not exist.".format(prm_fpath))
            return False

        num_params = None
        last_link_id = None
        attributes_set = 0
        all_topo_linkids = topology.keys()
        with open(prm_fpath, "r+") as rfile:
            for cur_line in rfile:
                cur_line = cur_line.strip()

                # read header
                if num_params is None:
                    num_params = int(cur_line)
                    continue

                # ignore blank lines
                if cur_line == "":
                    continue

                # process linkid line
                if last_link_id is None:
                    last_link_id = int(cur_line)
                    continue

                # process attributes line
                if last_link_id is not None:
                    slp_line = [float(v) for v in cur_line.split(" ")]
                    if last_link_id in all_topo_linkids:
                        topology[last_link_id].set_attributes(slp_line[0], slp_line[1], slp_line[2])
                        attributes_set += 1
                    last_link_id = None
                    continue

                print("fill_parameters: Unexpected end of loop.")

        # farewell check
        if attributes_set != len(all_topo_linkids):
            print("Set attributes for {0} out of {1} hillslope-links.".format(attributes_set, len(all_topo_linkids)))
            return False
        else:
            print("Set attributes for all {0} hillslope-links.".format(attributes_set))
            return True

    def __init__(self):
        return


# Static Class - Library of functions (its methods) for reading HDF5 files
class H5FileReader:

    @staticmethod
    def list_h5_files(input_fpath_arg):
        """
        Return list of all considered files.
        :param input_fpath_arg:
        :return:
        """

        # basic check
        if not os.path.exists(input_fpath_arg):
            print("File '{0}' does not exist.".format(input_fpath_arg))
            return None

        # list all files in same folder
        base_folder = os.path.dirname(input_fpath_arg)
        root_name = os.path.basename(input_fpath_arg).split("_")[0]
        return_list = []
        for cur_file_name in sorted(os.listdir(base_folder)):
            # only considers .h5 files
            if (not cur_file_name.endswith(".h5")) or (not cur_file_name.startswith(root_name)):
                continue

            cur_file_path = os.path.join(base_folder, cur_file_name)
            return_list.append(cur_file_path)

        return return_list

    @staticmethod
    def read_h5_file(h5_file_path):
        """
        Translate discharge content from h5 file into a dictionary of [link_id]->discharge
        :param h5_file_path:
        :return:
        """

        ret_dict = {}

        # get outlet's discharge
        with h5py.File(h5_file_path, "r") as hdf_file:
            hdf_file_content = hdf_file.get('snapshot')
            for i in range(len(hdf_file_content)):
                ret_dict[int(hdf_file_content[i][0])] = hdf_file_content[i][1]

        return ret_dict

    @staticmethod
    def read_h5_file_and_fill_snapshot(h5_file_path, snapshot):
        """
        Translate discharge content from h5 file into a dictionary of [link_id]->discharge
        :param h5_file_path:
        :param snapshot:
        :return:
        """

        # get outlet's discharge
        with h5py.File(h5_file_path, "r") as hdf_file:
            hdf_file_content = hdf_file.get('snapshot')
            for i in range(len(hdf_file_content)):
                cur_link_id = int(hdf_file_content[i][0])
                cur_channel_disc = hdf_file_content[i][1]
                cur_pond_wc = hdf_file_content[i][2]
                cur_tplr_wc = hdf_file_content[i][3]
                cur_subs_wc = hdf_file_content[i][4]
                cur_acc_rain_wc = hdf_file_content[i][5]

                snapshot.hl_states[cur_link_id].set_dischs_and_volume(cur_link_id, cur_channel_disc, cur_pond_wc,
                                                                      cur_tplr_wc, cur_subs_wc)

                snapshot.add_particles_from_rainfall(cur_link_id, cur_acc_rain_wc)

    @staticmethod
    def get_h5_file_timestamp(file_path):
        """

        :param file_path:
        :return:
        """

        extless = file_path.replace(".h5", "")
        timestamp_str = extless.split("_")[-1]
        return int(timestamp_str)

    def __init__(self):
        return


# Static Class - Library of functions (its methods) for dealing with multi-threading
class ThreadManager:

    __max_threads = 50        # number - constant
    _links = None             # array
    _threads_opened = None    # number - count
    _threads_closed = None    #
    _threads_finished = None  # number - count
    _topo = None              # constant_ref
    _parts_dict = None        # constant_ref
    _disch_dict = None
    _ret_dict = None
    _lock = _thread.allocate_lock()
    _count_seen_particles = None
    _count_seen_hilllinks = None

    @staticmethod
    def thread_call(sub_links_id, aThreadManager):
        """

        :param aThreadManager:
        :return:
        """

        while len(sub_links_id) > 0:
            a = sub_links_id.pop()
            # print("Going for {0} & {1}.".format(a, aThreadManager))
            ThreadManager.track_particles_in_link(a, aThreadManager)

    @staticmethod
    def track_particles_in_link(link_id, aThreadManager):
        """

        :param link_id:
        :param aThreadManager:
        :return:
        """

        cur_link_vol = OutputTracer.calculate_volume_in_link(aThreadManager._topo, aThreadManager._disch_dict, link_id)
        aThreadManager._count_seen_hilllinks += 1

        # print("aThreadManager._disch_dict: {0} / {1}".format(aThreadManager._disch_dict[link_id], cur_link_vol))

        prob_leave = aThreadManager._disch_dict[link_id] / cur_link_vol

        for cur_particle_idx in range(0, len(aThreadManager._parts_dict[link_id])):
            aThreadManager._count_seen_particles += 1
            count_times = GblVars.delta_t
            while count_times > 0:
                cur_rdm_val = np.random.uniform(0, 1)                                                     # limit tries
                if cur_rdm_val <= prob_leave:
                    cur_downlink_id = aThreadManager._topo[link_id].get_downstream_hl_id()
                    if (cur_downlink_id is not None) and (cur_downlink_id in aThreadManager._ret_dict.keys()):
                        aThreadManager._ret_dict[cur_downlink_id].append(aThreadManager._parts_dict[link_id][cur_particle_idx])  # got to flow
                    break
                count_times -= 1
            if count_times <= 0:
                aThreadManager._ret_dict[link_id].append(aThreadManager._parts_dict[link_id][cur_particle_idx])  # got stuck

        aThreadManager._threads_closed += 1

    def process_it(self, links):
        """

        :param links: []
        :return:
        """

        self._links = list(links)
        link_step = int(len(self._links) / ThreadManager.__max_threads)

        while (len(self._links) > 0) and (self._threads_opened < ThreadManager.__max_threads):

            _thread.start_new_thread(ThreadManager.thread_call, (self._links[link_step*self._threads_opened:
                                                                             link_step*(self._threads_opened+1)], self))
            self._threads_opened += 1

        while self._threads_closed < len(self._links):
            pass

        '''
        while (len(self._links) > 0) and (self._threads_opened < ThreadManager.__max_threads):
            ThreadManager._lock.acquire()
            self._threads_opened += 1
            _thread.start_new_thread(ThreadManager.track_particles_in_link, (self._links.pop(), self))
            ThreadManager._lock.release()

        while self._threads_finished < len(self._links):
            if (self._threads_closed > 0) and (len(self._links) > 0):
                ThreadManager._lock.acquire()
                self._threads_closed -= 1
                _thread.start_new_thread(ThreadManager.track_particles_in_link, (self._links.pop(), self))
                ThreadManager._lock.release()
            pass
        '''

        return self._ret_dict

    def set_args(self, topology, particles_dict, disch_dict):
        """

        :param topology:
        :param particles_dict:
        :param disch_dict: Discharge dictionary
        :return:
        """

        self._topo = topology
        self._parts_dict = particles_dict
        self._disch_dict = disch_dict
        self._ret_dict = {}
        for cur_link_id in self._topo.keys():
            self._ret_dict[cur_link_id] = []

    def __init__(self):
        self._threads_opened = 0
        self._threads_closed = 0
        self._threads_finished = 0
        self._count_seen_particles = 0
        self._count_seen_hilllinks = 0
        return