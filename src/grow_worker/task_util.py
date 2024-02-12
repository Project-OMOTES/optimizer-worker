import celery


class TaskUtil:
    def __init__(self, task: celery.Task):
        self.task = task

    def update_progress(self, fraction: float, message: str) -> None:
        self.task.send_event("task-progress-update", progress={"fraction": fraction, "message": message})
