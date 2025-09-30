from rq import Queue, Retry
from cache import cache_store
from rq.command import send_stop_job_command
from config import logger
from functools import wraps
from rq.job import JobStatus

q = Queue(name='conversation_coach', connection=cache_store)

def _handle_message(user_id):
    from app import create_app
    app = create_app()
    with app.app_context():
        from commands import handle_message
        handle_message(user_id)

def _handle_task(task_id):
    from app import create_app
    app = create_app()
    with app.app_context():
        from commands import handle_task
        handle_task(task_id)

def enqueue_message(user_id):
    q.enqueue(_handle_message, user_id, job_timeout='20m', job_id=user_id, retry=Retry(max=3))

def enqueue_task(task_id):
    q.enqueue(_handle_task, task_id, job_timeout='1h', job_id=task_id, retry=Retry(max=3))

def cancel_task(task_id):
    try:
        send_stop_job_command(cache_store, task_id)
    except Exception as e:
        logger.error(e)

def with_app_context(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from app import create_app
        app = create_app()
        with app.app_context():
            return f(*args, **kwargs)
    return decorated

class AsJob:
    FROMQUEUE_SIGNAL_KWARG = '__as_job_execution'
    def __init__(self, f, args, kwargs):
        self.f = f
        self.args = args
        self.kwargs = kwargs
        self.kwargs[AsJob.FROMQUEUE_SIGNAL_KWARG] = True
        self.job_id = f.__name__
        for arg in args:
            self.job_id += "_"+ str(arg)

    def enqueue(self, timeout='20m'):
        if self.is_pending():
            return
        q.enqueue(self.f, args=self.args, kwargs=self.kwargs, job_timeout=timeout, job_id=self.job_id, retry=Retry(max=3))
    
    def is_pending(self):
        return self.get_status() in [JobStatus.STARTED, JobStatus.QUEUED, JobStatus.SCHEDULED]

    def is_failed(self):
        if not self.get_status():
            return False
        return self.get_status() == JobStatus.FAILED

    def get_status(self):
        job = q.fetch_job(self.job_id)
        if not job:
            return None
        return job.get_status()

def as_job(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if kwargs.get(AsJob.FROMQUEUE_SIGNAL_KWARG):
            del kwargs[AsJob.FROMQUEUE_SIGNAL_KWARG]
            return f(*args, **kwargs)
        else:
            return AsJob(f, args, kwargs)
    return decorated

# @as_job
# @with_app_context
# def inspect_related_files_job(epic_id):
#     from models.epic import Epic
#     epic: Epic = Epic.query.get(epic_id)
#     epic.inspect_related_files()