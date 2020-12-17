import factory


class AppFactory(factory.django.DjangoModelFactory):
    label = factory.Faker("word")
    app_id = factory.Sequence(lambda n: f"app-{n}")

    class Meta:
        model = "credentials.App"


class AppServiceCredentialsFactory(factory.django.DjangoModelFactory):
    app = factory.SubFactory(AppFactory)
    service = factory.SubFactory("bptl.work_units.zgw.tests.factories.ServiceFactory")

    class Meta:
        model = "credentials.AppServiceCredentials"
