try:
    from fastai.basic_train import LearnerCallback
    import traceback

    HAS_FASTAI = True
except Exception as e:
    import_exception = "\n".join(
        traceback.format_exception(type(e), e, e.__traceback__)
    )
    HAS_FASTAI = False


class train_callback(LearnerCallback):
    def __init__(self, learn, stop_var):
        self.counter = 0
        self.stop_var = stop_var
        super().__init__(learn)

    def on_batch_end(self, **kwargs):
        # print(self.counter)
        self.counter += 1
        if self.counter > self.stop_var:
            self.counter = 0
            return {"stop_epoch": True}
