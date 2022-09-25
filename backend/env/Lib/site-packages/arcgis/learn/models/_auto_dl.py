from ._arcgis_model import ArcGISModel
import traceback
import json, time, datetime
from datetime import datetime as dt
import pandas as pd
from IPython.display import clear_output

try:
    import arcgis as ag
    import torch
    from . import MMSegmentation, MMDetection
    import matplotlib.pyplot as plt
    from ._autodl_utils import train_callback
    from ._arcgis_model import ArcGISModel
    import numpy as np
    import cv2, os

    HAS_FASTAI = True
except Exception as e:
    import_exception = "\n".join(
        traceback.format_exception(type(e), e, e.__traceback__)
    )
    HAS_FASTAI = False


class ImageryModel(ArcGISModel):
    """
    Imagery Model is used to fine tune models trained using AutoDL
    """

    def __init__(self):
        self._modeltype = None
        pass

    def load(self, path, data):
        """
        Loads a compatible saved model for inferencing or fine tuning from the disk,
        which can be used to further fine tune the models saved using AutoDL.

        =====================   ===========================================
        **Argument**            **Description**
        ---------------------   -------------------------------------------
        name_or_path            Required string. Name or Path to
                                Esri Model Definition(EMD) file.
        =====================   ===========================================
        """
        is_mm = False
        try:
            f = open(path)
            emd = json.load(f)
        except Exception as e:
            print(e)
            raise Exception("This method supports emd files only")
        try:
            modelname = emd["ModelName"]
            self._modeltype = emd["ModelType"]
            if "ModelFileConfigurationClass" in emd.keys():
                mm_model = emd["Kwargs"]["model"]
                is_mm = True
        except Exception as e:
            print(e)
            raise Exception("Not a valid emd file")
        if is_mm:
            setattr(
                self,
                "imagery_model",
                getattr(ag.learn, modelname)(data, model=mm_model),
            )
        else:
            setattr(self, "imagery_model", getattr(ag.learn, modelname)(data))
        getattr(self, "imagery_model").load(path)

    def fit(
        self,
        epochs=10,
        lr=None,
        one_cycle=True,
        early_stopping=False,
        checkpoint=True,
        tensorboard=False,
        monitor="valid_loss",
        **kwargs
    ):
        """
        Train the model for the specified number of epochs while using the
        specified learning rates

        =====================   ===========================================
        **Argument**            **Description**
        ---------------------   -------------------------------------------
        epochs                  Optional integer. Number of cycles of training
                                on the data. Increase it if the model is underfitting.
                                Default value is 10.
        ---------------------   -------------------------------------------
        lr                      Optional float or slice of floats. Learning rate
                                to be used for training the model. If ``lr=None``,
                                an optimal learning rate is automatically deduced
                                for training the model.
        ---------------------   -------------------------------------------
        one_cycle               Optional boolean. Parameter to select 1cycle
                                learning rate schedule. If set to `False` no
                                learning rate schedule is used.
        ---------------------   -------------------------------------------
        early_stopping          Optional boolean. Parameter to add early stopping.
                                If set to 'True' training will stop if parameter
                                `monitor` value stops improving for 5 epochs.
                                A minimum difference of 0.001 is required for
                                it to be considered an improvement.
        ---------------------   -------------------------------------------
        checkpoint              Optional boolean or string.
                                Parameter to save checkpoint during training.
                                If set to `True` the best model
                                based on `monitor` will be saved during
                                training. If set to 'all', all checkpoints
                                are saved. If set to False, checkpointing will
                                be off. Setting this parameter loads the best
                                model at the end of training.
        ---------------------   -------------------------------------------
        tensorboard             Optional boolean. Parameter to write the training log.
                                If set to 'True' the log will be saved at
                                <dataset-path>/training_log which can be visualized in
                                tensorboard. Required tensorboardx version=2.1

                                The default value is 'False'.
                                **Note - Not applicable for Text Models
        ---------------------   -------------------------------------------
        monitor                 Optional string. Parameter specifies
                                which metric to monitor while checkpointing
                                and early stopping. Defaults to 'valid_loss'. Value
                                should be one of the metric that is displayed in
                                the training table. Use `{model_name}.available_metrics`
                                to list the available metrics to set here.
        =====================   ===========================================
        """
        try:
            getattr(self, "imagery_model").fit(
                epochs,
                lr,
                one_cycle,
                early_stopping,
                checkpoint,
                tensorboard,
                monitor,
                **kwargs
            )
        except Exception as E:
            print("Load the model first using load()")

    def save(
        self,
        name_or_path,
        framework="PyTorch",
        publish=False,
        gis=None,
        compute_metrics=True,
        save_optimizer=False,
        save_inference_file=True,
        **kwargs
    ):
        """
        Saves the model weights, creates an Esri Model Definition and Deep
        Learning Package zip for deployment to Image Server or ArcGIS Pro.

        =====================   ===========================================
        **Argument**            **Description**
        ---------------------   -------------------------------------------
        name_or_path            Required string. Name of the model to save. It
                                stores it at the pre-defined location. If path
                                is passed then it stores at the specified path
                                with model name as directory name and creates
                                all the intermediate directories.
        ---------------------   -------------------------------------------
        framework               Optional string. Exports the model in the
                                specified framework format ('PyTorch', 'tflite'
                                'torchscript', and 'TF-ONXX' (deprecated)).
                                Only models saved with the default framework
                                (PyTorch) can be loaded using `from_model`.
                                ``tflite`` framework (experimental support) is
                                supported by ``SingleShotDetector``,
                                ``FeatureClassifier`` and ``RetinaNet``.
                                ``torchscript`` format is supported by
                                ``SiamMask``.
                                For usage of SiamMask model in ArcGIS Pro 2.8,
                                load the ``PyTorch`` framework saved model
                                and export it with ``torchscript`` framework
                                using ArcGIS API for Python v1.8.5.
                                For usage of SiamMask model in ArcGIS Pro 2.9,
                                set framework to ``torchscript`` and use the
                                model files additionally generated inside
                                'torch_scripts' folder.
                                If framework is ``TF-ONNX`` (Only supported for
                                ``SingleShotDetector``), ``batch_size`` can
                                be passed as an optional keyword argument.
        ---------------------   -------------------------------------------
        publish                 Optional boolean. Publishes the DLPK as an item.
        ---------------------   -------------------------------------------
        gis                     Optional GIS Object. Used for publishing the item.
                                If not specified then active gis user is taken.
        ---------------------   -------------------------------------------
        compute_metrics         Optional boolean. Used for computing model
                                metrics.
        ---------------------   -------------------------------------------
        save_optimizer          Optional boolean. Used for saving the model-optimizer
                                state along with the model. Default is set to False
        ---------------------   -------------------------------------------
        save_inference_file     Optional boolean. Used for saving the inference file
                                along with the model.
                                If False, the model will not work with ArcGIS Pro 2.6
                                or earlier. Default is set to True.
        ---------------------   -------------------------------------------
        kwargs                  Optional Parameters:
                                Boolean `overwrite` if True, it will overwrite
                                the item on ArcGIS Online/Enterprise, default False.
        =====================   ===========================================
        """
        getattr(self, "imagery_model").save(
            name_or_path,
            framework,
            publish,
            gis,
            compute_metrics,
            save_optimizer,
            save_inference_file,
            **kwargs
        )

    def lr_find(self, allow_plot=True):
        """
        Runs the Learning Rate Finder. Helps in choosing the
        optimum learning rate for training the model.

        =====================   ===========================================
        **Argument**            **Description**
        ---------------------   -------------------------------------------
        allow_plot              Optional boolean. Display the plot of losses
                                against the learning rates and mark the optimal
                                value of the learning rate on the plot.
                                The default value is 'True'.
        =====================   ===========================================
        """
        try:
            getattr(self, "imagery_model").lr_find(allow_plot)
        except Exception as E:
            print("Load the model first using load()")

    def available_metrics(self):
        """
        List of available metrics that are displayed in the training
        table. Set `monitor` value to be one of these while calling
        the `fit` method.
        """
        try:
            return getattr(self, "imagery_model").available_metrics
        except Exception as E:
            print("Load the model first using load()")

    def plot_losses(self):
        """
        Plot validation and training losses after fitting the model.
        """
        try:
            return getattr(self, "imagery_model").plot_losses()
        except Exception as E:
            print("Load the model first using load()")

    def unfreeze(self):
        """
        Unfreezes the earlier layers of the model for fine-tuning.
        """
        try:
            if hasattr(getattr(self, "imagery_model"), "unfreeze"):
                return getattr(self, "imagery_model").unfreeze()
            else:
                print("This model does not support unfreeze method")
        except Exception as E:
            print("Load the model first using load()")

    def mIOU(self):
        """
        Computes mean IOU on the validation set for each class.

        =====================   ===========================================
        **Argument**            **Description**
        ---------------------   -------------------------------------------
        mean                    Optional bool. If False returns class-wise
                                mean IOU, otherwise returns mean iou of all
                                classes combined.
        ---------------------   -------------------------------------------
        show_progress           Optional bool. Displays the progress bar if
                                True.
        =====================   ===========================================

        :return: `dict` if mean is False otherwise `float`
        """
        if self._modeltype is not None:
            if self._modeltype == "ObjectDetection":
                print("This method is not supported with Object Detection models")
                return
            else:
                try:
                    return getattr(self, "imagery_model").mIOU()
                except Exception as E:
                    print("Load the model first using load()")
        else:
            print("Train the model first using fit()")
            return

    def average_precision_score(self):
        """
        Computes average precision on the validation set for each class.

        =====================   ===========================================
        **Argument**            **Description**
        ---------------------   -------------------------------------------
        detect_thresh           Optional float. The probability above which
                                a detection will be considered for computing
                                average precision.
        ---------------------   -------------------------------------------
        iou_thresh              Optional float. The intersection over union
                                threshold with the ground truth labels, above
                                which a predicted bounding box will be
                                considered a true positive.
        ---------------------   -------------------------------------------
        mean                    Optional bool. If False returns class-wise
                                average precision otherwise returns mean
                                average precision.
        =====================   ===========================================

        :return: `dict` if mean is False otherwise `float`
        """
        if self._modeltype is not None:
            if self._modeltype != "ObjectDetection":
                print("This method is not supported with pixel classification model")
                return
            else:
                try:
                    return getattr(self, "imagery_model").average_precision_score()
                except Exception as E:
                    print("Load the model first using load()")
        else:
            print("Train the model first using fit()")
            return


class AutoDL:
    """
    Automates the process of model selection, training and hyperparameter tuning of
    arcgis.learn supported deep learning models within a specified time limit.

    =====================   ===========================================
    **Argument**            **Description**
    ---------------------   -------------------------------------------
    data                    Required ImageryDataObject. Returned data object from
                            `prepare_data` function.
    ---------------------   -------------------------------------------
    total_time_limit        Optional Int. The total time limit in hours for
                            AutoDL training.
                            Default is 5 Hr.
    ---------------------   -------------------------------------------
    mode                    Optional Str.
                            Can be "basic" or "perform".

                            basic : To to be used when the user wants to train all selected networks.
                            perform : To be used when the user wants to tune hyper parameters of two
                            best performing models from basic mode.
    ---------------------   -------------------------------------------
    network                 Optional List of str.
                            The list of models that will be used in the training.
                            For eg:
                            Supported Object Detection models:
                            ["SingleShotDetector", "RetinaNet", "FasterRCNN", "YOLOv3", "MMDetection"]
                            Supported Object Detection models:
                            ["DeepLab", "UnetClassifier", "PSPNetClassifier", "MMSegmentation"]
    ---------------------   -------------------------------------------
    verbose                 Optional Boolean.
                            To be used to display logs while training the models.
                            Default is True.

    =====================   ===========================================

    :return: `AutoDL` Object
    """

    def __init__(
        self, data=None, total_time_limit=5, mode="basic", network=None, verbose=True
    ):

        if verbose:
            self.logger_dict = []
        self._data = data
        self.verbose = verbose
        algorithms = network
        self._total_training_time = 350
        self._max_image_set = 500
        self._max_epochs = 20
        self._remaining_time = 0
        self._all_algorithms = [
            "DeepLab",
            "UnetClassifier",
            "PSPNetClassifier",
            "ann",
            "apcnet",
            "ccnet",
            "cgnet",
            "deeplabv3",
            "SingleShotDetector",
            "RetinaNet",
            "FasterRCNN",
            "YOLOv3",
            "atss",
            "carafe",
            "cascade_rcnn",
            "cascade_rpn",
            "dcn",
        ]
        self._all_mm_algorithms = [
            "ann",
            "apcnet",
            "ccnet",
            "cgnet",
            "deeplabv3",
            "atss",
            "carafe",
            "cascade_rcnn",
            "cascade_rpn",
            "dcn",
        ]
        self._train_df = None
        self._average_precision_score_df = None
        self._mIOU_df = None
        self.best_model = None
        self._all_losses = {}
        self._max_accuracy = 0
        self._train_callback = train_callback
        self._all_detection_data = [
            "PASCAL_VOC_rectangles",
            "KITTI_rectangles",
            "RCNN_Masks",
        ]
        if total_time_limit < 1:
            print("Total time limit should be greater than or equal to 1 hr")
            return
        total_time_limit = total_time_limit * 60
        self._training_mode = mode.lower()
        if self._training_mode == "basic":
            self._time_in_sec = total_time_limit * 60
        elif self._training_mode == "perform":
            self._time_in_sec = (total_time_limit * 60) // 2
        else:
            print("Please select a vaild mode for training..")
            return

        self._algos = []
        self._model_type = self._data._dataset_type

        if self._model_type == "Classified_Tiles":
            if algorithms is None:
                algorithms = self.supported_classification_models()
            all_algos = self.supported_classification_models()
            for algo in algorithms:
                if algo not in all_algos:
                    error = algo + " is not a supported classification model."
                    raise Exception(error)
                if algo == "MMSegmentation":
                    self._algos.extend(MMSegmentation.supported_models)
                else:
                    self._algos.append(algo)
        elif self._model_type in self._all_detection_data:
            if algorithms is None:
                algorithms = self.supported_detection_models()
            all_algos = self.supported_detection_models()
            for algo in algorithms:
                if algo not in all_algos:
                    error = algo + " is not a supported Object Detection model."
                    raise Exception(error)
                if algo == "MMDetection":
                    self._algos.extend(MMDetection.supported_models)
                else:
                    self._algos.append(algo)
        else:
            raise Exception("Data must be in ESRI defined format")

        model_stats = self._model_stats()
        for algo in self._algos:
            if algo in self._all_algorithms:
                self._total_training_time += int(model_stats[algo]["time"])

        self._total_training_time //= 60
        self._algos = self._sort_algos(self._algos)

        if total_time_limit is None:
            total_time_limit = self._total_training_time

        number_of_images = len(self._data.train_ds) + len(self._data.valid_ds)
        # print(number_of_images)
        required_time = (
            self._total_training_time * number_of_images
        ) // self._max_image_set

        self._tiles_required = (
            self._max_image_set * total_time_limit
        ) // self._total_training_time

        if self._tiles_required >= number_of_images:
            self._tiles_required = number_of_images

        if round(total_time_limit / 60, 2) == 1:
            unit = "hour"
        else:
            unit = "hours"
        print(
            "Given time to process the dataset is:",
            round(total_time_limit / 60, 2),
            unit,
        )
        print(
            "Number of images that can be processed in the given time:",
            self._tiles_required,
        )
        print(
            "Time required to process the entire dataset of",
            self._tiles_required,
            "images is",
            round(required_time / 60, 2),
            "hours",
        )

    def _train_model(
        self, model, backbone=None, epochs=20, model_type="classification"
    ):
        """
        Train the AutoDL models.
        """
        is_best = False
        start_time = time.time()
        if model_type == "classification":
            mm_model = "MMSegmentation"
        if model_type == "detection":
            mm_model = "MMDetection"
        if self.verbose:
            log_msg = "{date}: Initializing the {network} network...".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model
            )
            print(log_msg)
            self.logger_dict.append(log_msg)
        if backbone is None:
            if not self._model_stats()[model]["is_mm"]:
                setattr(self, model, getattr(ag.learn, model)(self._data))
                callbacks = [
                    self._train_callback(
                        getattr(self, model).learn,
                        self._tiles_required // self._data.batch_size,
                    )
                ]
            else:
                setattr(
                    self, model, getattr(ag.learn, mm_model)(self._data, model=model)
                )
                callbacks = [
                    self._train_callback(
                        getattr(self, model).learn,
                        self._tiles_required // self._data.batch_size,
                    )
                ]
            backbone = getattr(self, model)._backbone.__name__
        else:
            if not self._model_stats()[model]["is_mm"]:
                setattr(
                    self, model, getattr(ag.learn, model)(self._data, backbone=backbone)
                )
                callbacks = [
                    self._train_callback(
                        getattr(self, model).learn,
                        self._tiles_required // self._data.batch_size,
                    )
                ]
            else:
                setattr(
                    self, model, getattr(ag.learn, mm_model)(self._data, model=model)
                )
                callbacks = [
                    self._train_callback(
                        getattr(self, model).learn,
                        self._tiles_required // self._data.batch_size,
                    )
                ]

        if self.verbose:
            log_msg = "{date}: {network} initialized with {bk} backbone".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model, bk=backbone
            )
            print(log_msg)
            self.logger_dict.append(log_msg)
            log_msg = "{date}: Finding best learning rate for {network}".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model
            )
            print(log_msg)

            self.logger_dict.append(log_msg)
            # # clear_output(wait=True)
            # all_logs = "\n".join(self.logger_dict)
            # print(all_logs)

        lr_val = getattr(self, model).lr_find(allow_plot=False)
        if self.verbose:
            log_msg = "{date}: Best learning rate for {network} with the selected data is {lr}".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model, lr=lr_val
            )
            print(log_msg)
            self.logger_dict.append(log_msg)

            log_msg = "{date}: Fitting {network}".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model
            )
            print(log_msg)
            self.logger_dict.append(log_msg)

        try:
            getattr(self, model).fit(epochs, early_stopping=True, callbacks=callbacks)
            if self.verbose:
                clear_output(wait=True)
                all_logs = "\n".join(self.logger_dict)
                print(all_logs)
        except Exception as e:
            if self.verbose:
                all_logs = "\n".join(self.logger_dict)
                print(all_logs)
            else:
                print(e)

        if self.verbose:
            log_msg = "{date}: Training completed".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model
            )
            print(log_msg)
            self.logger_dict.append(log_msg)
        end_time = time.time()
        # print(metrics)
        if self.verbose:
            log_msg = "{date}: Computing the network metrices".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S")
            )
            print(log_msg)
            self.logger_dict.append(log_msg)
        metrics = getattr(self, model).learn.recorder.get_state()
        self._all_losses[model] = metrics["losses"]
        tot_sec = int(end_time - start_time)
        self.m = metrics
        #
        t = str(datetime.timedelta(seconds=tot_sec))
        torch.cuda.empty_cache()
        train_loss = np.array(metrics["losses"])[-1]
        valid_loss = np.array(metrics["val_losses"])[-1]

        if model_type == "classification":
            accuracy = np.array(metrics["metrics"])[-1][0]
            miou = getattr(self, model).mIOU()
            miou["Model"] = str(model)
            self._mIOU_df = pd.concat(
                [
                    self._mIOU_df,
                    pd.DataFrame({key: [val] for key, val in miou.items()}),
                ]
            )
            if accuracy >= self._max_accuracy:
                is_best = True
                self._max_accuracy = accuracy
            dice = np.array(metrics["metrics"])[-1][1]
            df = pd.DataFrame(
                {
                    "Model": [model],
                    "train_loss": [train_loss],
                    "valid_loss": [valid_loss],
                    "accuracy": [accuracy],
                    "dice": [dice],
                    "lr": [lr_val],
                    "training time": [t],
                    "backbone": [backbone],
                }
            )
            self._train_df = pd.concat([self._train_df, df], ignore_index=True)
        else:
            avg_precision = getattr(self, model).average_precision_score()
            avg = sum(avg_precision.values()) / len(avg_precision.values())
            avg_precision["Model"] = str(model)
            self._average_precision_score_df = pd.concat(
                [
                    self._average_precision_score_df,
                    pd.DataFrame({key: [val] for key, val in avg_precision.items()}),
                ]
            )
            if avg >= self._max_accuracy:
                is_best = True
                self._max_accuracy = avg
            df = pd.DataFrame(
                {
                    "Model": [model],
                    "train_loss": [train_loss],
                    "valid_loss": [valid_loss],
                    "average_precision_score": [avg],
                    "lr": [lr_val],
                    "training time": [t],
                    "backbone": [backbone],
                }
            )
            self._train_df = pd.concat([self._train_df, df], ignore_index=True)
        if self.verbose:
            log_msg = "{date}: Finished training {network}.".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model
            )
            print(log_msg)
            self.logger_dict.append(log_msg)
            log_msg = "{date}: Exiting...".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S")
            )
            print(log_msg)
            self.logger_dict.append(log_msg)

        ## Save the model
        if self.verbose:
            log_msg = "{date}: Saving the model".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S")
            )
            print(log_msg)
            self.logger_dict.append(log_msg)

        getattr(self, model).save("AutoDL_" + str(model) + "_" + backbone)
        if self.verbose:
            log_msg = "{date}: model saved at {path}".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                path=os.path.join(
                    self._data.path, "models", "AutoDL_" + str(model) + "_" + backbone
                ),
            )
            print(log_msg)
            self.logger_dict.append(log_msg)
        if not self._model_stats()[model]["is_mm"]:
            setattr(
                self, model + "_backbones", getattr(self, model).supported_backbones
            )
        if is_best:
            self.best_model = model
            setattr(self, "BestPerformingModel", getattr(self, model))
        else:
            delattr(self, model)
            torch.cuda.empty_cache()
            if self.verbose:
                log_msg = "{date}: deleting {network} with {bk}".format(
                    date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                    network=model,
                    bk=backbone,
                )
                print(log_msg)
                self.logger_dict.append(log_msg)
        return tot_sec

    def fit(self, **kwargs):
        """
        Train the selected networks for the specified number of epochs and using the
        specified learning rates
        """
        if self._model_type == "Classified_Tiles":
            m_type = "classification"
            self._train_df = pd.DataFrame(
                columns=[
                    "Model",
                    "train_loss",
                    "valid_loss",
                    "accuracy",
                    "dice",
                    "lr",
                    "training time",
                    "backbone",
                ]
            )
        elif self._model_type in self._all_detection_data:
            m_type = "detection"
            self._train_df = pd.DataFrame(
                columns=[
                    "Model",
                    "train_loss",
                    "valid_loss",
                    "average_precision_score",
                    "lr",
                    "training time",
                    "backbone",
                ]
            )

        compare_time = self._time_in_sec
        if self.verbose:
            log_msg = "{date}: Selected networks: {networks}".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                networks=" ".join(self._algos),
            )
            print(log_msg)
            self.logger_dict.append(log_msg)
        for model in self._algos:
            if self.verbose:
                log_msg = "{date}: Current network - {network}... ".format(
                    date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model
                )
                print(log_msg)
                self.logger_dict.append(log_msg)
            model_time = self._model_stats()[model]["time"]
            model_time = (model_time * self._tiles_required) // self._max_image_set
            mt = str(datetime.timedelta(seconds=model_time))
            if self.verbose:
                log_msg = "{date}: Total time alloted to train the {network} model is {network_time}".format(
                    date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                    network=model,
                    network_time=mt,
                )
                print(log_msg)
                self.logger_dict.append(log_msg)
            if model_time > compare_time:
                epochs = (self._max_epochs * compare_time) // model_time
                if self.verbose:
                    log_msg = """{date}: Remaining time is not sufficient to train the {network} for complete 20 epochs, \
                    instead it will be trained for {net_epochs}""".format(
                        date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                        network=model,
                        net_epochs=epochs,
                    )
                    print(log_msg)
                    self.logger_dict.append(log_msg)
            else:
                epochs = self._max_epochs
                if self.verbose:
                    log_msg = """{date}: Maximum number of epochs will be {net_epochs} to train {network}""".format(
                        date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                        network=model,
                        net_epochs=epochs,
                    )
                    self.logger_dict.append(log_msg)
                    print(log_msg)

            if epochs == 0:
                if self.verbose:
                    log_msg = """{date}: The time left to train the {network} is not sufficent...""".format(
                        date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model
                    )
                    print(log_msg)
                    self.logger_dict.append(log_msg)
                    log_msg = """{date}: Stopping the training process...""".format(
                        date=dt.now().strftime("%d-%m-%Y %H:%M:%S")
                    )
                    print(log_msg)
                    self.logger_dict.append(log_msg)
                break

            tot_sec = self._train_model(model, epochs=epochs, model_type=m_type)
            compare_time -= tot_sec

        if m_type == "classification":
            self._train_df = self._train_df.sort_values(
                "accuracy", ascending=False
            ).reset_index(drop=True)
        if m_type == "detection":
            self._train_df = self._train_df.sort_values(
                "average_precision_score", ascending=False
            ).reset_index(drop=True)

        if self._training_mode == "perform":
            if self.verbose:
                log_msg = """{date}: Entering into exhaustive mode...""".format(
                    date=dt.now().strftime("%d-%m-%Y %H:%M:%S")
                )
                print(log_msg)
                self.logger_dict.append(log_msg)
            compare_time = self._time_in_sec
            top_models = list(self._train_df.head(2)["Model"])
            all_trained_models = list(self._train_df["Model"])
            if self.verbose:
                log_msg = (
                    """{date}: Top two performing models are - {network}""".format(
                        date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                        network=" ".join(top_models),
                    )
                )
                print(log_msg)
                self.logger_dict.append(log_msg)

            counter = 0
            for model in all_trained_models:
                if counter >= 2:
                    break
                if self.verbose:
                    log_msg = "{date}: Starting training {network}... ".format(
                        date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model
                    )
                    print(log_msg)
                    self.logger_dict.append(log_msg)
                model_time = self._model_stats()[model]["time"]
                model_time = (model_time * self._tiles_required) // self._max_image_set
                if self.verbose:
                    log_msg = "{date}: Total time alloted to train the {network} model is {network_time}".format(
                        date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                        network=model,
                        network_time=mt,
                    )
                    print(log_msg)
                    self.logger_dict.append(log_msg)
                if model_time > compare_time:
                    epochs = (self._max_epochs * compare_time) // model_time
                    if self.verbose:
                        log_msg = """{date}: Remaining time is not sufficient to train the {network} for complete 20 epochs, 
                                        max epochs will be {net_epochs}""".format(
                            date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                            network=model,
                            net_epochs=epochs,
                        )
                        print(log_msg)
                        self.logger_dict.append(log_msg)
                else:
                    epochs = self._max_epochs
                    if self.verbose:
                        log_msg = """{date}: Maximum number of epochs will be {net_epochs} to train {network}""".format(
                            date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                            network=model,
                            net_epochs=epochs,
                        )
                        self.logger_dict.append(log_msg)
                        print(log_msg)

                if epochs == 0:
                    if self.verbose:
                        log_msg = """{date}: The time left to train the {network} is not sufficent...""".format(
                            date=dt.now().strftime("%d-%m-%Y %H:%M:%S"), network=model
                        )
                        print(log_msg)
                        self.logger_dict.append(log_msg)
                        log_msg = """{date}: Stopping the training process...""".format(
                            date=dt.now().strftime("%d-%m-%Y %H:%M:%S")
                        )
                        print(log_msg)
                        self.logger_dict.append(log_msg)
                    break
                if self._model_stats()[model]["is_mm"]:
                    log_msg = """{date}: {model} does not have additional backbones, skipping...""".format(
                        date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                        model=model,
                    )
                    print(log_msg)
                    self.logger_dict.append(log_msg)
                    continue

                all_bb = getattr(self, model + "_backbones")
                selected_bb = []
                for bb in all_bb:
                    bkbone = "".join([b for b in bb if not b.isdigit()])
                    if bkbone not in selected_bb:
                        selected_bb.append(bb)
                        selected_bb.append(bkbone)
                supported_backbone = selected_bb[::2]
                if self.verbose:
                    log_msg = (
                        """{date}: Selected backbones for {model}: {bb} ...""".format(
                            date=dt.now().strftime("%d-%m-%Y %H:%M:%S"),
                            model=model,
                            bb=" ".join(supported_backbone),
                        )
                    )
                    print(log_msg)
                    self.logger_dict.append(log_msg)
                all_bb = list(
                    self._train_df.loc[self._train_df["Model"] == model]["backbone"]
                )
                for bb in supported_backbone:
                    if bb in all_bb:
                        print("skipping backbone-", bb, "for model-", model)
                        continue
                    tot_sec = self._train_model(
                        model, backbone=bb, epochs=epochs, model_type=m_type
                    )
                    compare_time -= tot_sec
                counter += 1
        if self.verbose:
            log_msg = (
                """{date}: Collating and evaluating model performances...""".format(
                    date=dt.now().strftime("%d-%m-%Y %H:%M:%S")
                )
            )
            print(log_msg)
            self.logger_dict.append(log_msg)
        if m_type == "classification":
            self._train_df = self._train_df.sort_values(
                "accuracy", ascending=False
            ).reset_index(drop=True)
        if m_type == "detection":
            self._train_df = self._train_df.sort_values(
                "average_precision_score", ascending=False
            ).reset_index(drop=True)

        if self.verbose:
            log_msg = """{date}: Exiting...""".format(
                date=dt.now().strftime("%d-%m-%Y %H:%M:%S")
            )
            print(log_msg)
            self.logger_dict.append(log_msg)

    def show_results(self, rows=5, **kwargs):
        """
        Shows sample results for the model.

        =====================   ===========================================
        **Argument**            **Description**
        ---------------------   -------------------------------------------
        rows                    Optional number of rows. By default, 5 rows
                                are displayed.
        =====================   ===========================================

        :returns dataframe
        """
        print(
            "show_results will only show the output from the best performing model: "
            + self.best_model
        )
        plt.show(
            getattr(self, "BestPerformingModel").show_results(
                rows=rows, thresh=1, **kwargs
            )
        )
        pass

    def _display_plot(self, x, y):
        plt.bar(x, y)
        plt.xticks(rotation=60)
        plt.show()
        pass

    def score(self, allow_plot=False):
        """
        returns output from AutoDL's model.score(), "average precision score" in case of detection and accuracy in case of classification.
        """
        if self._train_df is None:
            raise Exception("Train a model using fit() before getting the scores.")
        else:
            if allow_plot:
                if self._model_type == "Classified_Tiles":
                    self._display_plot(
                        self._train_df["Model"], self._train_df["accuracy"]
                    )
                else:
                    self._display_plot(
                        self._train_df["Model"],
                        self._train_df["average_precision_score"],
                    )
            return self._train_df

    def average_precision_score(self):
        """
        Calculates the average of the "average precision score" of all classes for selected networks
        """
        if self._model_type == "Classified_Tiles":
            print("This method is not supported with the selected model type")
        elif self._model_type in self._all_detection_data:
            if self._average_precision_score_df is None:
                print("Please train the networks first using fit()")
                return
            cols = ["Model"] + list(self._average_precision_score_df.keys())[:-1]
            return self._average_precision_score_df[cols]
        else:
            print("Datatype not supported!!")

    def mIOU(self):
        """
        Calculates the mIOU of all classes for selected networks
        """
        if self._model_type == "Classified_Tiles":
            try:
                cols = ["Model"] + list(self._mIOU_df.keys())[:-1]
                return self._mIOU_df[cols]
            except Exception as E:
                print(E)
                print("Please train the networks first using fit()")

        elif self._model_type in self._all_detection_data:
            print("This method is not supported with the selected model type")
        else:
            print("Datatype not supported!!")

    def _model_stats(self):
        """
        Shows the model stats
        """
        details = {
            "DeepLab": {"time": 1600, "is_mm": False, "executed": False},
            "UnetClassifier": {"time": 6550, "is_mm": False, "executed": False},
            "PSPNetClassifier": {"time": 6550, "is_mm": False, "executed": False},
            "ann": {
                "time": 1550,
                "is_mm": True,
            },
            "apcnet": {
                "time": 1650,
                "is_mm": True,
            },
            "ccnet": {
                "time": 3500,
                "is_mm": True,
            },
            "cgnet": {
                "time": 700,
                "is_mm": True,
            },
            "deeplabv3": {
                "time": 4200,
                "is_mm": True,
            },
            "SingleShotDetector": {"time": 1600, "is_mm": False, "executed": False},
            "RetinaNet": {"time": 6550, "is_mm": False, "executed": False},
            "FasterRCNN": {"time": 6550, "is_mm": False, "executed": False},
            "YOLOv3": {
                "time": 1550,
                "is_mm": False,
            },
            "atss": {
                "time": 1650,
                "is_mm": True,
            },
            "carafe": {
                "time": 3500,
                "is_mm": True,
            },
            "cascade_rcnn": {
                "time": 700,
                "is_mm": True,
            },
            "cascade_rpn": {
                "time": 4200,
                "is_mm": True,
            },
            "dcn": {
                "time": 4200,
                "is_mm": True,
            },
        }
        return details

    def _sort_algos(self, algorithms):
        """
        Sorts algorithms in a particular order
        """
        sorted_algos = []
        algos = self._all_algorithms
        for algo in algos:
            if algo in algorithms:
                sorted_algos.append(algo)
        return sorted_algos

    def supported_classification_models(self):
        """
        Supported classification models.
        """
        return ["DeepLab", "UnetClassifier", "PSPNetClassifier", "MMSegmentation"]

    def supported_detection_models(self):
        """
        Supported detection models.
        """
        return [
            "SingleShotDetector",
            "RetinaNet",
            "FasterRCNN",
            "YOLOv3",
            "MMDetection",
        ]

    def lr_find(self):
        print("lr_find() is not supported in AutoDL")
