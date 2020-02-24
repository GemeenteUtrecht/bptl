import factory
import factory.fuzzy
from zgw_consumers.constants import APITypes

from bptl.tasks.tests.factories import TaskMappingFactory


class ServiceFactory(factory.django.DjangoModelFactory):
    label = factory.Faker("word")
    api_type = factory.fuzzy.FuzzyChoice(choices=APITypes.values)
    api_root = factory.Faker("url")

    class Meta:
        model = "zgw_consumers.Service"


class DefaultServiceFactory(factory.django.DjangoModelFactory):
    task_mapping = factory.SubFactory(TaskMappingFactory)
    service = factory.SubFactory(ServiceFactory)
    alias = factory.Faker("word")

    class Meta:
        model = "zgw.DefaultService"
