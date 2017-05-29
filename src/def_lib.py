
class ArgumentsManager:

    @staticmethod
    def get_str(sys_args, arg_id):
        """

        :param sys_args: Array of string. I would REALLY appreciate if you use the sys.argv here. Really.
        :param arg_id: String. Example "-linkid".
        :return:
        """

        # basic check
        if (sys_args is None) or (arg_id is None):
            return None

        if (arg_id in sys_args) and (sys_args.index(arg_id) < (len(sys_args) - 1)):
            return sys_args[sys_args.index(arg_id) + 1]
        else:
            return None

    @staticmethod
    def get_int(sys_args, arg_id):
        """

        :param sys_args:
        :param arg_id:
        :return:
        """

        arg_value = ArgumentsManager.get_str(sys_args, arg_id)
        if arg_value is not None:
            try:
                return int(ArgumentsManager.get_str(sys_args, arg_id))
            except ValueError:
                print("Argument '{0}' is not an integer ({1}).".format(arg_id, arg_value))
                return None
        else:
            return None

    @staticmethod
    def get_flt(sys_args, arg_id):
        """

        :param sys_args:
        :param arg_id:
        :return:
        """

        arg_value = ArgumentsManager.get_str(sys_args, arg_id)
        if arg_value is not None:
            try:
                return float(ArgumentsManager.get_str(sys_args, arg_id))
            except ValueError:
                print("Argument '{0}' is not an float ({1}).".format(arg_id, arg_value))
                return None
        else:
            return None

    def __init__(self):
        return
