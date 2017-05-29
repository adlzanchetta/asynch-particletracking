import json


class ConfigFile:

    ROOT = "asynch_parttrack_conf"
    PART = "particles"
    WATE = "watershed"
    WATE_LINK = "outlet_link_id"
    WATE_RVRF = "rvr_file_path"
    WATE_PRMF = "prm_file_path"
    SIMU = "simulation"
    SIMU_HDF5 = "hdf5_file_path"
    SIMU_BINF = "particle_track_file_path"

    _json_file_content = None

    def __init__(self, json_file_path):
        """

        :param json_file_path:
        :return:
        """

        with open(json_file_path, "r") as r_file:
            json_content = json.load(r_file)
            json_root = json_content[ConfigFile.ROOT]
            self._json_file_content = json_root

        return

    def get_first_h5_file_path(self):
        return self._get(lvl_1=ConfigFile.WATE, lvl_2=ConfigFile.SIMU_HDF5)

    def get_particle_track_file_path(self):
        return self._get(lvl_1=ConfigFile.WATE, lvl_2=ConfigFile.SIMU_BINF)

    def get_outlet_link_id(self):
        return self._get(lvl_1=ConfigFile.WATE, lvl_2=ConfigFile.WATE_LINK)

    def get_rvr_file_path(self):
        return self._get(lvl_1=ConfigFile.WATE, lvl_2=ConfigFile.WATE_RVRF)

    def get_prm_file_path(self):
        return self._get(lvl_1=ConfigFile.WATE, lvl_2=ConfigFile.WATE_PRMF)

    def _get(self, lvl_1=None, lvl_2=None, lvl_3=None):
        """

        :param lvl_1:
        :param lvl_2:
        :param lvl_3:
        :return:
        """

        if None not in (lvl_1, lvl_2, lvl_3):
            try:
                return self._json_file_content[lvl_1][lvl_2][lvl_3]
            except KeyError:
                print("Missing key '{0}' > '{1}' > '{2}'.".format(lvl_1, lvl_2, lvl_3))
                return None

        elif None not in (lvl_1, lvl_2):
            try:
                return self._json_file_content[lvl_1][lvl_2]
            except KeyError:
                print("Missing key '{0}' > '{1}'.".format(lvl_1, lvl_2))
                return None

        elif lvl_1 is not None:
            try:
                return self._json_file_content[lvl_1]
            except KeyError:
                print("Missing key '{0}' > '{1}'.".format(lvl_1))
                return None
        else:
            return None