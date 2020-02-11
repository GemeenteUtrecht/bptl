import factory
import factory.fuzzy


class TaskMappingFactory(factory.django.DjangoModelFactory):
    topic_name = factory.fuzzy.FuzzyChoice(["initalize-zaak", "set-zaak-status"])
    callback = "bptl.dummy.tasks.dummy"

    class Meta:
        model = "tasks.TaskMapping"
