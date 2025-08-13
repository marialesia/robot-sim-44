# tasks/inspection_task.py
from .base_task import BaseTask

class InspectionTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="Inspection")
