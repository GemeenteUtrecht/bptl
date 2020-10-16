from dataclasses import dataclass
from typing import Optional

from zgw_consumers.api_models.base import Model, factory
from bptl.tasks.base import check_variable

from datetime import datetime

@dataclass
class EmailPerson(Model):
    sender: dict

    @property
    def name(self) -> str:
        return check_variable(self.sender, 'name')
    
    @property
    def email(self) -> str:
        return check_variable(self.sender, 'email')


@dataclass
class Email(Model):
    email: dict

    @property
    def subject(self) -> str:
        return check_variable(self.email, 'subject')
    
    @property
    def content(self) -> str:
        return check_variable(self.email, 'content')


@dataclass
class EmailContext(Model):
    context: dict

    @property
    def kownslFrontendUrl(self) -> str:
        return check_variables(self.context, 'kownslFrontendUrl')

    @property
    def reminder(self) -> str:
        return check_variables(self.context, 'reminder')

    @property
    def deadline(self) -> datetime:
        return check_variables(self.context, 'deadline')


@dataclass
class SendEmail(Model):
    variables: dict

    @property
    def sender(self) -> EmailPerson:
        sender = check_variable(self.variables, 'sender')
        return factory(EmailPerson, {'sender': sender})

    @property
    def receiver(self) -> EmailPerson:
        receiver = check_variable(self.variables, 'receiver')
        return factory(EmailPerson, {'receiver':receiver})
    
    @property
    def email(self) -> Email:
        email = check_variables(self.variables, 'email')
        return factory(Email, email)
    
    @property
    def context(self) -> EmailContext:
        context = check_variables(self.variables, 'context')
        return factory(EmailContext, context)
    
    @property
    def template(self) -> str:
        return check_variables(self.variables, 'template')