# tasks/packaging_task.py
from .base_task import BaseTask

class PackagingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Packaging")
