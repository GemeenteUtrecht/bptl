from dataclasses import dataclass
from zgw_consumers.api_models.base import Model

@dataclass
class EmailPerson(Model):
    name: str
    email: str


@dataclass
class Email(Model):
    subject: str
    body: str
