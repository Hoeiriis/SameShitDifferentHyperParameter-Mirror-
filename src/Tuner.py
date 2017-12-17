import numpy as np
import pandas as pd
import keras.callbacks as cb
from src.parameter_config.ParamConfig import ParamConfig
from src.suggestors.SuggestorBase import ParamLog
from src.suggestors import RandomSearch, ZoomRandomSearch
from src.utils import cd


class Tuner:

    def __init__(self, name, sam, param_config, suggestors, save_path, evaluators=None, param_log=None):
        """
        Tuner class, the main component of SameShitDifferentHyperparameter. It does automatic hyperparameter
        tuning
        :param name: Name of the tuner, uesd for saving purposes. Type: string
        :param sam: Useless param name. Anyway, it is the class instance that has hyperparameters to tune.
        It should have the following functions:
        sam.run: Given a hyperparameter suggestion, do its thing and return a score indicating the performance of that
                 hyperparameter suggestion.
        sam.save_model: A function for saving the model if needed. Only necessary if save_model is set to True in
                        function tune.
        sam.set_callbacks: A function for injecting callbacks, such as EarlyStopping, into the model.

        :param param_config: configuration of the parameters. Type: list of SingleParam
        :param suggestors: suggestor names of the suggestors used for parameter suggestion. Type: list of strings
        :param save_path: storage path for saving trials. Type: string
        :param evaluators: skip for now
        :param param_log: log of tried parameters, default is None in which case a new param log i started.
               Type: ParamLog
        """
        self.tuner_name = name
        self.sam = sam
        self.save_path = save_path
        self.suggestors_dict = {"RandomSearch": self._make_random_search,
                                "ZoomRandomSearch": self._make_zoom_random_search}

        # Making rescaler dictionary
        p_config = ParamConfig()
        self.rescaler_functions, self.param_names = p_config.make_rescale_dict(param_config)

        # Starting log
        self.param_log = ParamLog(len(self.rescaler_functions), param_descriptions=self.param_names)\
            if param_log is None else param_log

        if type(suggestors) is list:
            self.suggestors = self._initialize_suggestors(suggestors)
        elif type(suggestors) is str:
            self.suggestors = self._initialize_suggestors([suggestors])
        # elif issubclass(type(suggestors), SuggestorBase):
        #     self.suggestors = [suggestors]
        elif type(suggestors) is dict:
            self.suggestors = self._initialize_suggestors_from_dict(suggestors)
        else:
            raise TypeError("Parameter suggestor should be of type dict, string or list"
                            " but is of type {}".format(type(suggestors)))

    def tune(self, stop_tuning, live_evals=True, save_model=False):

        trials = 0
        previous_param_performance = None
        while not stop_tuning(trials):
            param_suggestion = self._get_param_suggestions()
            # todo: evals
            previous_param_performance = self.sam.run(params=param_suggestion)

            self.param_log.log_score(previous_param_performance)
            self._save_log(save_model=save_model)

            trials = trials+1

    def _save_log(self, save_model=False):

        actual = self.param_log.get_actual_params()
        unscaled = self.param_log.get_unscaled_params()
        score = self.param_log.get_score()

        # Constructing csv
        parameter_df = pd.DataFrame(data=score, columns=["Score"])
        joined = pd.DataFrame(data=actual, columns=self.param_names).join(parameter_df)

        with cd(self.save_path):
            # Saving numpy arrays
            np.save("{}_params_actual.npy".format(self.tuner_name), actual)
            np.save("{}_params_unscaled.npy".format(self.tuner_name), unscaled)
            np.save("{}_params_scores.npy".format(self.tuner_name), score)

            # # Saving csv
            # heading = self.param_names
            # heading.append("Score")
            joined.to_csv("{}_params_score".format(self.tuner_name), index=False)

            if save_model:
                self.sam.save("{}_param_{}".format(self.tuner_name, len(actual)))

    def _get_param_suggestions(self):

        param_suggestions = []
        for suggestor in self.suggestors:
            param_suggestions.append(suggestor.suggest_parameters())

        return self._choose_param_suggestion(param_suggestions)

    def _choose_param_suggestion(self, param_suggestion_list):
        # print("Warning: Choosing parameters from multiple suggestors has not been implemented yet."
        #       "Returning the first entry of the param_suggestion_list.")
        return param_suggestion_list[0]

    def _initialize_suggestors(self, suggestor_list):
        suggestors = []
        for entry in suggestor_list:
            if entry in self.suggestors_dict.keys():
                suggestors.append(self.suggestors_dict[entry]())
            else:
                raise Exception("{} is not an existing suggestor".format(entry))

        return suggestors

    def _initialize_suggestors_from_dict(self, suggestor_dict):
        suggestors = []
        for name, kwargs in suggestor_dict.items():
            if name in self.suggestors_dict.keys():
                suggestors.append(self.suggestors_dict[name](**kwargs))
            else:
                raise Exception("{} is not an existing suggestor".format(name))

        return suggestors

    def set_callbacks(self):
        actual = self.param_log.get_actual_params()

        model_checkpoint = cb.ModelCheckpoint(save_best_only=True,
                                              monitor='val_loss',
                                              filepath=self.save_path+"{}_param_{}".format(self.tuner_name, len(actual)))
        early_stopping = cb.EarlyStopping(monitor="val_loss", patience=10)

        reduce_lr = cb.ReduceLROnPlateau(monitor='val_loss', factor=0.1,
                                         patience=4, min_lr=0.00001)

        callbacks = [model_checkpoint, early_stopping, reduce_lr]
        self.sam.set_callbacks(callbacks)

    def _make_random_search(self):
        return RandomSearch(self.rescaler_functions, self.param_names, self.param_log)

    def _make_zoom_random_search(self, trials_per_zoom=None, n_eval_trials=None):
        return ZoomRandomSearch(trials_per_zoom=20 if trials_per_zoom is None else trials_per_zoom,
                                n_eval_trials=3 if n_eval_trials is None else n_eval_trials,
                                rescale_functions=self.rescaler_functions,
                                param_names=self.param_names,
                                param_log=self.param_log)
