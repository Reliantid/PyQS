import json
import logging

import boto3

from .utils import function_to_import_path

logger = logging.getLogger("pyqs")

conn = None


def get_or_create_queue(queue_name):
    global conn
    if conn is None:
        conn = boto3.client('sqs')
    queue = conn.get_queue_url(QueueName=queue_name)
    if queue.get('QueueUrl'):
        return queue['QueueUrl']
    else:
        return client.create_queue(QueueName=queue_name)['QueueUrl']


def task_delayer(func_to_delay, queue_name, delay_seconds=0, override=False):
    function_path = function_to_import_path(func_to_delay, override=override)

    if not queue_name:
        # If no queue specified, use the function_path for the queue
        queue_name = function_path

    def wrapper(*args, **kwargs):
        queue = get_or_create_queue(queue_name)

        _delay_seconds = delay_seconds
        if '_delay_seconds' in kwargs:
            _delay_seconds = kwargs['_delay_seconds']
            del kwargs['_delay_seconds']

        logger.info("Delaying task %s: %s, %s", function_path, args, kwargs)
        message_dict = {
            'task': function_path,
            'args': args,
            'kwargs': kwargs,
        }

        conn.send_message(QueueUrl=queue, DelaySeconds=delay_seconds,
          MessageBody=json.dumps(message_dict))

    return wrapper


class task(object):
    def __init__(self, queue=None, delay_seconds=0, custom_function_path=None):
        self.queue_name = queue
        self.delay_seconds = delay_seconds
        self.function_path = custom_function_path

    def __call__(self, *args, **kwargs):
        func_to_wrap = args[0]
        function = func_to_wrap
        override = False
        if self.function_path:
            override = True
            function = self.function_path
        func_to_wrap.delay = task_delayer(function, self.queue_name, self.delay_seconds, override=override)
        return func_to_wrap
