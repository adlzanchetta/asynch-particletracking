import json
import os


class ConfigFile:

    ROOT = "asynch_parttrack_conf"
    PART = "particles"
    PART_INIT = "initial_distribution"
    PART_RAIN = "rainfall_distribution"
    PART_METH = "method"
    PART_METH_EQUL = "all_equal"
    PART_METH_PROP = "volume_proportional"
    PART_METH_NONE = "none"
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

    # ### particles ### #

    def get_particles_initdist_method(self):
        return self._get(lvl_1=ConfigFile.PART, lvl_2=ConfigFile.PART_INIT, lvl_3=ConfigFile.PART_METH)

    def get_particles_raindist_method(self):
        return self._get(lvl_1=ConfigFile.PART, lvl_2=ConfigFile.PART_RAIN, lvl_3=ConfigFile.PART_METH)

    # ### watershed ### #

    def get_outlet_link_id(self):
        return self._get(lvl_1=ConfigFile.WATE, lvl_2=ConfigFile.WATE_LINK)

    def get_rvr_file_path(self):
        return self._get(lvl_1=ConfigFile.WATE, lvl_2=ConfigFile.WATE_RVRF)

    def get_prm_file_path(self):
        return self._get(lvl_1=ConfigFile.WATE, lvl_2=ConfigFile.WATE_PRMF)

    # ### simulation ### #

    def get_first_h5_file_path(self):
        return self._get(lvl_1=ConfigFile.SIMU, lvl_2=ConfigFile.SIMU_HDF5)

    def get_particle_track_file_path(self):
        return self._get(lvl_1=ConfigFile.SIMU, lvl_2=ConfigFile.SIMU_BINF)

    # ### checks ### #

    def check_consistancy(self):
        """

        :return: Boolean. TRUE if file is ok and ready to go, FALSE otherwise.
        """

        all_ok = True

        # mandatory tag
        all_ok = all_ok if ConfigFile._check_file_exists(self.get_first_h5_file_path()) else False

        # mandatory tags - input file references
        all_ok = all_ok if ConfigFile._check_integer(self.get_outlet_link_id()) else False
        all_ok = all_ok if ConfigFile._check_file_exists(self.get_rvr_file_path()) else False
        all_ok = all_ok if ConfigFile._check_file_exists(self.get_prm_file_path()) else False

        # mandatory tags -
        all_ok = all_ok if ConfigFile._check_str_value(self.get_particles_initdist_method(),
                                                       (ConfigFile.PART_METH_EQUL, ConfigFile.PART_METH_PROP,
                                                        ConfigFile.PART_METH_NONE),
                                                       True) else False

        return True if all_ok else False

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

    @staticmethod
    def _check_integer(tag_value):
        """

        :param tag_value:
        :return:
        """

        if tag_value is None:
            return False
        try:
            int(tag_value)
            return True
        except ValueError:
            print("CHECK FAIL: '{0}' is not a integer.".format(tag_value))
            return False

    @staticmethod
    def _check_str_value(tag_value, valid_values, mandatory):
        """

        :param tag_value:
        :param valid_values:
        :param mandatory:
        :return:
        """

        if (tag_value is None) and mandatory:
            print("CHECK FAIL: Missing mandatory value.".format(tag_value, valid_values))
            return False
        elif (tag_value is None) and not mandatory:
            return True
        elif (tag_value is not None) and (tag_value in valid_values):
            return True
        else:
            print("CHECK FAIL: '{0}' does not match ({1}).".format(tag_value, valid_values))
            return False


    @staticmethod
    def _check_file_exists(file_path):
        """

        :param file_path:
        :return:
        """

        if file_path is None:
            return False

        if not os.path.exists(file_path):
            print("CHECK FAIL: '{0}' does not exist.".format(file_path))
            return False

        return True
