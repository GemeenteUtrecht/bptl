from bptl.tasks.base import WorkUnit
from bptl.tasks.registry import register

from .client import ZACClient

@register
class UserDetailsTask(WorkUnit):
    client = ZACClient()
    client.task = self.task

    