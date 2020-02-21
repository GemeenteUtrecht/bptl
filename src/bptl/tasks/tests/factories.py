import factory
import factory.fuzzy
from zgw_consumers.constants import APITypes


class TaskMappingFactory(factory.django.DjangoModelFactory):
    topic_name = factory.fuzzy.FuzzyChoice(["initalize-zaak", "set-zaak-status"])
    callback = "bptl.dummy.tasks.dummy"

    class Meta:
        model = "tasks.TaskMapping"


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
        model = "tasks.DefaultService"
