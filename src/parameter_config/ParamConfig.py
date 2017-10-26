import numpy as np
from .rescalers import *


class ParamConfig:

    def __init__(self, param_config, run_function=None):

        self.param_config = param_config

        self.scale_functions = {}

    def make_rescale_functions(self):
        raise NotImplementedError

    def _integer_type(self, range, scaling=None, incremental=None):
        min_range = min(range)
        max_range = max(range)

        if scaling is None:
            scaling = "incremental"

        if scaling == "incremental":
            if incremental is None:
                incremental = 1

            return incremental_rescaler(incremental, (min_range, max_range))

        elif scaling == "log":
            return log_rescaler((min_range, max_range), int_log=True)

        else:
            raise ValueError("The given scaling \"{}\" is not supported".format(scaling))

    def _double(self, range, scaling=None, incremental=None):
        min_range = min(range)
        max_range = max(range)

        if scaling is None:
            scaling = "incremental"

        if scaling == "incremental":
            if incremental is None:
                incremental = (max_range - min_range) / 100

            return incremental_rescaler(incremental, (min_range, max_range))

        elif scaling == "log":
            return log_rescaler((min_range, max_range))

        else:
            raise ValueError("The given scaling \"{}\" is not supported".format(scaling))

    def _discrete(self, discrete_values):
        min_range = 0
        max_range = len(discrete_values)

        return create_min_max_rescaler((min_range, max_range), (0, 1))




if __name__ == "__main__":

    param_config = {
        "learning_rate": ("double", (0.0001, 0.01), "log"),
        "dropout_1": ("double", (0, 0.7), "incremental", 0.05),
        "hidden_size_1": ("integer", (100, 1000), "incremental", 50),
        "batch_size": ("discrete", [64, 128, 256, 512, 1024])
    }

    tuner = ParamConfig(param_config=param_config)
