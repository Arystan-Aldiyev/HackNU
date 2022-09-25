from logging import exception
from ._arcgis_model import ArcGISModel, _EmptyData
from .._data import _raise_fastai_import_error
from ._codetemplate import image_translation_prf
import traceback, json

try:
    from ._pix2pix_hd_utils import Pix2PixHDModel, Pix2PixHDLoss, Pix2PixHDTrainer
    from fastai.vision import Learner, partial, optim
    from .._data_utils.pix2pix_data import show_results, predict
    from .._utils.common import _get_emd_path, get_multispectral_data_params_from_emd
    from ._pix2pix_utils import compute_fid_metric, compute_metrics
    from pathlib import Path
    import torch

    HAS_FASTAI = True
except Exception as e:
    import_exception = "\n".join(
        traceback.format_exception(type(e), e, e.__traceback__)
    )
    HAS_FASTAI = False


class Pix2PixHD(ArcGISModel):

    """
    Creates a model object which generates fake images of type B from type A.

    =====================   ===========================================
    **Argument**            **Description**
    ---------------------   -------------------------------------------
    data                    Required fastai Databunch. Returned data object from
                            `prepare_data` function.
    ---------------------   -------------------------------------------
    pretrained_path         Optional string. Path where pre-trained model is
                            saved.
    =====================   ===========================================

    **kwargs**

    =====================   ===========================================
    n_gen_filters           Number of gen filters in first conv layer.
    ---------------------   -------------------------------------------
    gen_network             Selects model to use for generator.
    ---------------------   -------------------------------------------
    n_downsample_global     Number of downsampling layers in gen_network
    ---------------------   -------------------------------------------
    n_blocks_global         Number of residual blocks in the global
                            generator network.
    ---------------------   -------------------------------------------
    n_local_enhancers       Number of local enhancers to use.
    ---------------------   -------------------------------------------
    n_blocks_local          number of residual blocks in the local
                            enhancer network.
    ---------------------   -------------------------------------------
    norm                    instance normalization or batch normalization
    ---------------------   -------------------------------------------
    lsgan                   Use least square GAN, if True,
                            use vanilla GAN.
    ---------------------   -------------------------------------------
    n_dscr_filters          number of discriminator filters in first conv layer.
    ---------------------   -------------------------------------------
    n_layers_dscr           only used if which_model_net_dscr==n_layers.
    ---------------------   -------------------------------------------
    n_dscr                  number of discriminators to use.
    ---------------------   -------------------------------------------
    feat_loss               if 'True', use discriminator
                            feature matching loss.
    ---------------------   -------------------------------------------
    vgg_loss                if 'True', use VGG feature matching loss.
    ---------------------   -------------------------------------------
    lambda_feat             weight for feature matching loss.
    =====================   ===========================================

    :return: `Pix2PixHD` Object
    """

    def __init__(self, data, pretrained_path=None, *args, **kwargs):
        super().__init__(data)
        self._check_dataset_support(data)
        # input_nc=3, output_nc=3,
        vgg_loss = kwargs.get("vgg_loss", True)
        lambda_feat = kwargs.get("lambda_feat", 10.0)

        self.input_nc, self.output_nc = 3, 3
        label_nc = self._data.label_nc
        if self._data._is_multispectral:
            self.input_nc, self.output_nc = self._data.n_channel, self._data.n_channel
            vgg_loss = False
        elif self._data.label_nc:
            self.input_nc = label_nc
        pix2pix_hd = Pix2PixHDModel(label_nc, self.input_nc, self.output_nc, **kwargs)

        self.learn = Learner(
            data,
            pix2pix_hd,
            loss_func=Pix2PixHDLoss(pix2pix_hd, vgg_loss, lambda_feat),
            callback_fns=[Pix2PixHDTrainer],
            opt_func=partial(optim.Adam, betas=(0.5, 0.99)),
        )

        self.learn.model = self.learn.model.to(self._device)
        self._slice_lr = False
        if pretrained_path is not None:
            self.load(pretrained_path)
        self._code = image_translation_prf

        def __str__(self):
            return self.__repr__()

        def __repr__(self):
            return "<%s>" % (type(self).__name__)

    def show_results(self, rows=2, **kwargs):
        """
        Displays the results of a trained model on a part of the validation set.

        =====================   ===========================================
        **Argument**            **Description**
        ---------------------   -------------------------------------------
        rows                    Optional int. Number of rows of results
                                to be displayed.
        =====================   ===========================================

        """
        show_results(self, rows, **kwargs)

    @classmethod
    def from_model(cls, emd_path, data=None):

        """
        Creates a Pix2PixHD object from an Esri Model Definition (EMD) file.

        =====================   ===========================================
        **Argument**            **Description**
        ---------------------   -------------------------------------------
        emd_path                Required string. Path to Deep Learning Package
                                (DLPK) or Esri Model Definition(EMD) file.
        ---------------------   -------------------------------------------
        data                    Required fastai Databunch or None. Returned data
                                object from `prepare_data` function or None for
                                inferencing.
        =====================   ===========================================

        :return: `Pix2PixHD` Object
        """
        if not HAS_FASTAI:
            _raise_fastai_import_error(import_exception=import_exception)

        emd_path = _get_emd_path(emd_path)
        with open(emd_path) as f:
            emd = json.load(f)

        model_file = Path(emd["ModelFile"])

        if not model_file.is_absolute():
            model_file = emd_path.parent / model_file

        model_params = emd["ModelParameters"]
        resize_to = emd.get("resize_to")
        chip_size = emd["ImageHeight"]
        norm_stats = emd.get("norm_stats")

        if data is None:
            data = _EmptyData(
                path=emd_path.parent, loss_func=None, c=2, chip_size=resize_to
            )
            if emd.get("IsMultispectral", False):
                data = get_multispectral_data_params_from_emd(data, emd)

                normalization_stats_b = dict(emd.get("NormalizationStats_b"))
                for _stat in normalization_stats_b:
                    if normalization_stats_b[_stat] is not None:
                        normalization_stats_b[_stat] = torch.tensor(
                            normalization_stats_b[_stat]
                        )
                    setattr(data, ("_" + _stat), normalization_stats_b[_stat])

            data._is_multispectral = emd.get("IsMultispectral", False)
            data.n_channel = emd.get("n_intput_channel", None)
            if data.n_channel == None:
                data.n_channel = emd.get("n_channel", None)
            data.label_nc = emd.get("label_nc", None)
            data.output_nc = emd.get("output_nc", None)
            data.mask_map = emd.get("mask_map", None)
            data.emd_path = emd_path
            data.emd = emd
            data._is_empty = True
            data.resize_to = chip_size
            data.norm_stats = norm_stats

        return cls(data, **model_params, pretrained_path=str(model_file))

    def _get_emd_params(self, save_inference_file):
        _emd_template = {}
        _emd_template["Framework"] = "arcgis.learn.models._inferencing"
        _emd_template["ModelConfiguration"] = "_pix2pix_hd"
        _emd_template["InferenceFunction"] = "ArcGISImageTranslation.py"
        _emd_template["ModelType"] = "Pix2PixHD"
        _emd_template["n_intput_channel"] = self.output_nc
        _emd_template["label_nc"] = self._data.label_nc
        if self._data.label_nc != 0:
            _emd_template["mask_map"] = self._data.mask_map.tolist()
        # _emd_template["input_nc"] = self.input_nc

        norm_stats = []
        for k in self._data.norm_stats:
            norm_stats.append(k)
        _emd_template["norm_stats"] = list(norm_stats)
        # _emd_template["SupportsVariableTileSize"] = True
        # if self._data._is_multispectral:
        _emd_template["NormalizationStats_b"] = {
            "band_min_values": self._data._band_min_values_b,
            "band_max_values": self._data._band_max_values_b,
            "band_mean_values": self._data._band_mean_values_b,
            "band_std_values": self._data._band_std_values_b,
            "scaled_min_values": self._data._scaled_min_values_b,
            "scaled_max_values": self._data._scaled_max_values_b,
            "scaled_mean_values": self._data._scaled_mean_values_b,
            "scaled_std_values": self._data._scaled_std_values_b,
        }
        for _stat in _emd_template["NormalizationStats_b"]:
            if _emd_template["NormalizationStats_b"][_stat] is not None:
                _emd_template["NormalizationStats_b"][_stat] = _emd_template[
                    "NormalizationStats_b"
                ][_stat].tolist()
        _emd_template["n_channel"] = len(
            _emd_template["NormalizationStats_b"]["band_min_values"]
        )
        return _emd_template

    @property
    def _model_metrics(self):
        return self.compute_metrics()

    def predict(self, path):
        """
        Predicts and display the image.

        =====================   ===========================================
        **Argument**            **Description**
        ---------------------   -------------------------------------------
        img_path                Required path of an image.
        =====================   ===========================================

        """
        return predict(self, path)

    def compute_metrics(self, accuracy=True, show_progress=True):
        """
        Computes Peak Signal-to-Noise Ratio (PSNR) and
        Structural Similarity Index Measure (SSIM) on validation set.

        """
        psnr, ssim = compute_metrics(self, self._data.valid_dl, show_progress)
        if self._data._is_multispectral:
            fid = None
            return {"PSNR": "{0:1.4e}".format(psnr), "SSIM": "{0:1.4e}".format(ssim)}
        else:
            fid = compute_fid_metric(self, self._data)
            return {
                "PSNR": "{0:1.4e}".format(psnr),
                "SSIM": "{0:1.4e}".format(ssim),
                "FID": "{0:1.4e}".format(fid),
            }

    @property
    def supported_datasets(self):
        """Supported dataset types for this model."""
        return Pix2PixHD._supported_datasets()

    @staticmethod
    def _supported_datasets():
        return ["Pix2Pix", "Export_Tiles"]
