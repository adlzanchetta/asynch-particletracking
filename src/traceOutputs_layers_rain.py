from __future__ import division
from traceOutputs_lib import GblVars, AsynchFilesReader, H5FileReader, OutputTracer, DomainSnapshot, ParticleManager
from configFileReader_lib import ConfigFile
from def_lib import ArgumentsManager
import numpy as np
import datetime
import random
import pickle
import math
import h5py
import sys
import os


# ###################################################### HELP ######################################################## #

if '-h' in sys.argv:
    print("Performs the simulation of particles flow.")
    print("Usage 01: python traceOutputs_layers_rain.py -config CONFIG_JSON")
    print("  CONFIG_JSON : File path for a json configuration file.")
    print("Usage 02: python traceOutputs_layers_rain.py -in_first_h5 IN_H5 -in_rvr IN_RVR -in_prm IN_PRM -link_id LINK_ID -out_hyd OUT_HYD [-max_parts PARTS] [-all_parts ALL_PARTS] [-vol_per_parts VOL_PARTS]")
    print("  IN_H5       : First .h5 file in an output sequency of snapshots.")
    print("  IN_RVR      : File path for .rvr describing the topology of the network.")
    print("  IN_PRM      : File path for .prm describing the fillslope-links in the network.")
    print("  LINK_ID     : Integer with the link id of the link to which an hydrograph will be generated.")
    print("  OUT_HYD     : Path for output hydrograph binary file.")
    print("  PARTS       : Number of particles to be set in the initial condition of the observed link.")
    print("  ALL_PARTS   : Number of particles to be set in the initial condition each layer of each link.")
    print("  VOL_PARTS   : Volume of water (in cubic meters) that is represented by a rain particle.")
    quit()


# ###################################################### ARGS ######################################################## #

# get arguments
config_json_fpath_arg = ArgumentsManager.get_str(sys.argv, '-config')
input_fh5_fpath_arg = ArgumentsManager.get_str(sys.argv, '-in_first_h5')
input_rvr_fpath_arg = ArgumentsManager.get_str(sys.argv, '-in_rvr')
input_prm_fpath_arg = ArgumentsManager.get_str(sys.argv, '-in_prm')
linkid_arg = ArgumentsManager.get_int(sys.argv, '-link_id')
output_fpath_arg = ArgumentsManager.get_str(sys.argv, '-out_hyd')
max_part_arg = ArgumentsManager.get_int(sys.argv, '-max_parts')
all_part_arg = ArgumentsManager.get_int(sys.argv, '-all_parts')
vol_part_arg = ArgumentsManager.get_flt(sys.argv, '-vol_per_parts')

# basic checks
if config_json_fpath_arg is None:
    if input_fh5_fpath_arg is None:
        print("Missing '-in_first_h5' argument.")
        quit()
    if input_rvr_fpath_arg is None:
        print("Missing '-in_rvr' argument.")
        quit()
    if input_prm_fpath_arg is None:
        print("Missing '-in_prm' argument.")
        quit()
    if linkid_arg is None:
        print("Missing '-link_id' argument.")
        quit()
    if output_fpath_arg is None:
        print("Missing '-out_hyd' argument.")
        quit()
    if (max_part_arg is not None) and (all_part_arg is not None):
        print("Too many arguments: or '-max_parts', or '-all_parts', or none of them are expected, not both.")
        quit()


# ###################################################### DEFS ######################################################## #


def extract_timestamp_from_filepath(h5_file_path):
    """

    :param h5_file_path:
    :return:
    """
    base_name = os.path.splitext(h5_file_path)[0]
    return int(base_name.split("_")[-1])


def debug_parts(the_snapshot):
    """

    :param the_snapshot:
    :return:
    """

    parts_total, parts_dict = the_snapshot.count_particles_by_layer_source()
    print("Count parts 1b = {0}".format(parts_total))
    print("...from ponds: {0}.".format(parts_dict[ParticleManager.LAYER_POND]))
    print("...from toplayer: {0}.".format(parts_dict[ParticleManager.LAYER_TOPLAYER]))
    print("...from subsurface: {0}.".format(parts_dict[ParticleManager.LAYER_SUBSURFACE]))
    print("...from channel: {0}.".format(parts_dict[ParticleManager.LAYER_CHANNEL]))
    print("...from rain:'{0}'.".format(parts_dict[ParticleManager.LAYER_RAIN]))


def read_config_and_perform_traking(config_json_fpath):
    """

    :param config_json_fpath:
    :return:
    """

    # basic check
    if not os.path.exists(config_json_fpath):
        print("File '{0}' does not exist.".format(config_json_fpath))
        return

    # read file
    json_config_file = ConfigFile(config_json_fpath)
    ref_h5_fpath = json_config_file.get_first_h5_file_path()
    rvr_fpath = json_config_file.get_rvr_file_path()
    prm_fpath = json_config_file.get_prm_file_path()
    outlet_linkid = json_config_file.get_outlet_link_id()
    hydrograph_fpath = json_config_file.get_particle_track_file_path()
    max_part = None
    all_part = None
    vol_part = None

    # call function
    perform_tracking(ref_h5_fpath, rvr_fpath, prm_fpath, outlet_linkid, hydrograph_fpath, max_part=max_part,
                     all_part=all_part, vol_part=vol_part)


def perform_tracking(ref_h5_fpath, rvr_fpath, prm_fpath, outlet_linkid, hydrograph_fpath, max_part=None, all_part=None,
                     vol_part=None):
    """
    Central function of the script.
    :param ref_h5_fpath:
    :param rvr_fpath:
    :param prm_fpath:
    :param outlet_linkid:
    :param hydrograph_fpath:
    :param max_part:
    :param all_part:
    :param vol_part:
    :return:
    """

    # build parameters
    domain_prm = AsynchFilesReader.build_topology(rvr_fpath)
    AsynchFilesReader.fill_parameters(domain_prm, prm_fpath)
    GblVars.domain_structure = domain_prm
    GblVars.vol_particles = 0 if vol_part is None else vol_part

    '''
    if True:
        print("--QUIT() DEBUG--")
        quit()
    '''

    # list all h5 files and basic check it
    all_h5_files = H5FileReader.list_h5_files(ref_h5_fpath)
    if (all_h5_files is None) or (len(all_h5_files) == 0):
        print("Not enough files in '{0}'.".format(ref_h5_fpath))
        return

    # separate initial condition file
    ini_h5_file_path = all_h5_files[0]
    ini_h5_file_timestamp = H5FileReader.get_h5_file_timestamp(ini_h5_file_path)

    # create initial conditions for particles
    if (max_part is not None) and (all_part is None):
        init_cond = OutputTracer.distribute_particles_proportional(topology, all_h5_files[0], max_part, outlet_linkid)
    elif (max_part is None) and (all_part is not None):
        init_cond = OutputTracer.distribute_particles_equally(timestamp=ini_h5_file_timestamp, parts_in_pounds=all_part,
                                                              parts_in_toplayer=all_part, parts_in_subsurface=all_part,
                                                              parts_in_channel=all_part)
        print("Created snapshot with {0} states.".format(len(init_cond.hl_states)))
    else:
        print("Missing information for initial condition.")
        return

    # debug 1
    print("Count parts 1a = {0}".format(init_cond.count_particles()))
    print("...at '{0}'.".format(datetime.datetime.now()))

    # debug 2
    debug_parts(init_cond)

    #
    limit_files = None
    cur_cond = init_cond
    contrib_links_dict = {}
    total_files = len(all_h5_files)
    for count_files, cur_h5_file_path in enumerate(all_h5_files):
        cur_file_timestamp = extract_timestamp_from_filepath(cur_h5_file_path)
        next_cond = advance_particles(cur_h5_file_path, cur_cond)
        cur_cond.outlet_link_id = outlet_linkid
        # contrib_links_dict[cur_file_timestamp] = next_cond.get_contributing_links()
        contrib_links_dict[cur_file_timestamp] = cur_cond.get_contributing_links(aggregate_rain=True)

        '''
        print("Total particles at {0}: {1} to {2}.".format(count_files, cur_cond.count_particles(),
                                                           next_cond.count_particles()))
        '''
        print("File {0} of {1}.".format(count_files, total_files))
        cur_cond = next_cond
        if (limit_files is not None) and (count_files >= limit_files):
            break

        # debug 2
        debug_parts(cur_cond)

    # writing binary file
    with open(hydrograph_fpath, "wb+") as wfile:
        pickle.dump(contrib_links_dict, wfile)
    print("Wrote file '{0}'.".format(hydrograph_fpath))

    return


def calculate_volume_in_link(disch_dict, link_id):
    """

    :param topo:
    :param disch_dict:
    :param link_id:
    :return:
    """

    chan_len = GblVars.domain_structure[link_id].get_link_length()
    chan_aup = GblVars.domain_structure[link_id].get_upstream_area()
    chan_ahl = GblVars.domain_structure[link_id].get_hillslope_area()
    chan_dsc = disch_dict[link_id]

    # print("Link length: {0}".format(chan_len))

    tau = ((1 - GblVars.lambda_1) * chan_len * 1000)/(GblVars.vel_ref * (chan_aup**GblVars.lambda_2))
    vol_disch = tau * ((chan_dsc**(1 - GblVars.lambda_1))/(1 - GblVars.lambda_1))

    return vol_disch


def advance_particles(h5_file_path, cur_snapshot):
    """

    :param h5_file_path:
    :param cur_snapshot:
    :param volume_particles:
    :return: New dictionary with new particles condition
    """

    count_links_dbg = 10

    # disch_dict = H5FileReader.read_h5_file(h5_file_path)
    H5FileReader.read_h5_file_and_fill_snapshot(h5_file_path, cur_snapshot)
    the_timestamp = H5FileReader.get_h5_file_timestamp(h5_file_path)

    # create new empty domain snapshot
    ret_snapshot = DomainSnapshot(hillslopelink_ids=cur_snapshot.hl_states.keys(), the_timestamp=the_timestamp)
    ret_snapshot.inherit_cummulated_rained_parts(cur_snapshot)

    # iterate and move particles
    total_links = len(cur_snapshot.hl_states.keys())
    for i, cur_link_id in enumerate(cur_snapshot.hl_states.keys()):

        # estimate channel volume and prob. of leaving it
        # cur_link_vol = calculate_volume_in_link(disch_dict, cur_link_id)
        cur_link_vol = cur_snapshot.hl_states[cur_link_id].volum_chnl
        cur_link_dsc = cur_snapshot.hl_states[cur_link_id].disch_chnl
        prob_leave_cc = cur_link_dsc / cur_link_vol
        prob_leave_sc = cur_snapshot.hl_states[cur_link_id].volum_subs / cur_snapshot.hl_states[cur_link_id].disch_ssch
        prob_leave_ts = cur_snapshot.hl_states[cur_link_id].volum_tplr / cur_snapshot.hl_states[cur_link_id].disch_tlss
        prob_leave_pc = cur_snapshot.hl_states[cur_link_id].volum_pond / cur_snapshot.hl_states[cur_link_id].disch_pdch
        prob_leave_pt = cur_snapshot.hl_states[cur_link_id].volum_pond / cur_snapshot.hl_states[cur_link_id].disch_pdtl
        prob_leave_pt += prob_leave_pc

        # debug
        '''
        if count_links_dbg > 0:
            print("{0} <- {1}".format(total_links, i))
            print("Link {0}: {1:.4f}/{2:.4f} = {3:.4f}".format(cur_link_id, cur_link_dsc, cur_link_vol, prob_leave_cc))
            print("Link {0}: {1:.4f}/{2:.4f} = {3:.4f}".format(cur_link_id,
                                                               cur_snapshot.hl_states[cur_link_id].disch_ssch,
                                                               cur_snapshot.hl_states[cur_link_id].volum_subs,
                                                               prob_leave_sc))
            print("Link {0}: {1:.4f}/{2:.4f} = {3:.4f}".format(cur_link_id,
                                                               cur_snapshot.hl_states[cur_link_id].disch_tlss,
                                                               cur_snapshot.hl_states[cur_link_id].volum_tplr,
                                                               prob_leave_ts))
            print("Link {0}: {1:.4f}/{2:.4f} = {3:.4f}".format(cur_link_id,
                                                               cur_snapshot.hl_states[cur_link_id].disch_pdch,
                                                               cur_snapshot.hl_states[cur_link_id].volum_pond,
                                                               prob_leave_pc))
            print("Link {0}: {1:.4f}/{2:.4f} = {3:.4f}".format(cur_link_id,
                                                               cur_snapshot.hl_states[cur_link_id].disch_pdtl,
                                                               cur_snapshot.hl_states[cur_link_id].volum_pond,
                                                               prob_leave_pt))
            count_links_dbg -= 1
            if count_links_dbg == 0:
                print(" (...)")
                count_links_dbg -= 1
        '''

        # move particles from one channel to other
        for cur_particle in cur_snapshot.hl_states[cur_link_id].parts_chnl_frnt:
            count_times = GblVars.delta_t
            while count_times > 0:
                cur_rdm_val = np.random.uniform(0, 1)                                                     # limit tries
                if cur_rdm_val <= prob_leave_cc:
                    cur_downlink_id = GblVars.domain_structure[cur_link_id].get_downstream_hl_id()
                    if (cur_downlink_id is not None) and (cur_downlink_id in ret_snapshot.hl_states.keys()):
                        ret_snapshot.hl_states[cur_downlink_id].parts_chnl_frnt.append(cur_particle)  # particle flowed
                    break
                count_times -= 1
            if count_times <= 0:
                ret_snapshot.hl_states[cur_link_id].parts_chnl_frnt.append(cur_particle)           # particle got stuck

        # move particles from sub surface to channel
        for cur_particle in cur_snapshot.hl_states[cur_link_id].parts_subs_frnt:
            count_times = GblVars.delta_t
            while count_times > 0:
                cur_rdm_val = np.random.uniform(0, 1)
                if cur_rdm_val <= prob_leave_sc:
                    ret_snapshot.hl_states[cur_link_id].parts_chnl_frnt.append(cur_particle)
                    break
                count_times -= 1
            if count_times <= 0:
                ret_snapshot.hl_states[cur_link_id].parts_subs_frnt.append(cur_particle)

        # move particles from top layer to sub surface
        for cur_particle in cur_snapshot.hl_states[cur_link_id].parts_topl_frnt:
            count_times = GblVars.delta_t
            while count_times > 0:
                cur_rdm_val = np.random.uniform(0, 1)
                if cur_rdm_val <= prob_leave_ts:
                    ret_snapshot.hl_states[cur_link_id].parts_subs_frnt.append(cur_particle)
                    break
                count_times -= 1
            if count_times <= 0:
                ret_snapshot.hl_states[cur_link_id].parts_topl_frnt.append(cur_particle)

        # move particles from ponds to top layer or to channel
        for cur_particle in cur_snapshot.hl_states[cur_link_id].parts_pond_frnt:
            count_times = GblVars.delta_t
            while count_times > 0:
                cur_rdm_val = np.random.uniform(0, 1)
                if cur_rdm_val <= prob_leave_pc:
                    ret_snapshot.hl_states[cur_link_id].parts_chnl_frnt.append(cur_particle)
                    break
                elif cur_rdm_val <= prob_leave_pt:
                    ret_snapshot.hl_states[cur_link_id].parts_topl_frnt.append(cur_particle)
                    break
                count_times -= 1
            if count_times <= 0:
                ret_snapshot.hl_states[cur_link_id].parts_pond_frnt.append(cur_particle)

    #
    return ret_snapshot


# ###################################################### RUNS ######################################################## #

if config_json_fpath_arg is None:
    perform_tracking(input_fh5_fpath_arg, input_rvr_fpath_arg, input_prm_fpath_arg, linkid_arg, output_fpath_arg,
                     max_part=max_part_arg, all_part=all_part_arg, vol_part=vol_part_arg)
else:
    read_config_and_perform_traking(config_json_fpath_arg)
print("So far, so done!")
