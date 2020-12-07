from unittest.mock import patch

from django.test import TestCase
from django.utils.translation import gettext as _

from zgw_consumers.constants import APITypes

from bptl.tasks.registry import WorkUnitRegistry
from bptl.tasks.tests.factories import ServiceFactory

from ..forms import DefaultServiceFormset

register = WorkUnitRegistry()


@register
@register.require_service(APITypes.zrc)
def task_1(task):
    pass


@register
@register.require_service(APITypes.orc, alias="svc1")
@register.require_service(APITypes.orc)
def task_2(task):
    pass


MANAGEMENT_FORM = {
    "defaultservice_set-TOTAL_FORMS": 1,
    "defaultservice_set-INITIAL_FORMS": 0,
    "defaultservice_set-MIN_NUM_FORMS": 0,
    "defaultservice_set-MAX_NUM_FORMS": 10,
}


class RequiredServicesValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zrc = ServiceFactory.create(api_type=APITypes.zrc)
        cls.drc = ServiceFactory.create(api_type=APITypes.drc)
        cls.orc1 = ServiceFactory.create(api_type=APITypes.orc)
        cls.orc2 = ServiceFactory.create(api_type=APITypes.orc)

    def setUp(self):
        super().setUp()

        patcher = patch("bptl.tasks.forms.register", new=register)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_missing_alias(self):
        data = {
            "topic_name": "topic",
            "callback": "bptl.tasks.tests.test_validate_required_services.task_2",
            "defaultservice_set-0-alias": "",
            "defaultservice_set-0-service": self.orc1.pk,
        }
        formset = DefaultServiceFormset(data={**MANAGEMENT_FORM, **data})

        result = formset.is_valid()

        self.assertFalse(result)
        self.assertIn(
            _("Missing service alias '{alias}'").format(alias="svc1"),
            formset.non_form_errors(),
        )

    def test_alias_present_wrong_service_type(self):
        data = {
            "topic_name": "topic",
            "callback": "bptl.tasks.tests.test_validate_required_services.task_2",
            "defaultservice_set-0-alias": "svc1",
            "defaultservice_set-0-service": self.zrc.pk,
        }
        formset = DefaultServiceFormset(data={**MANAGEMENT_FORM, **data})

        result = formset.is_valid()

        self.assertFalse(result)
        self.assertFalse(formset.forms[0].is_valid())

        self.assertIn(
            _("The service for alias '{alias}' must be a '{api_type}' service.").format(
                alias="svc1",
                api_type=APITypes.labels[APITypes.orc],
            ),
            formset.forms[0].errors["service"],
        )

    def test_missing_service_type(self):
        data = {
            "topic_name": "topic",
            "callback": "bptl.tasks.tests.test_validate_required_services.task_1",
            "defaultservice_set-0-alias": "",
            "defaultservice_set-0-service": self.drc.pk,
        }
        formset = DefaultServiceFormset(data={**MANAGEMENT_FORM, **data})

        result = formset.is_valid()

        self.assertFalse(result)
        self.assertIn(
            _(
                "Missing a service of type '{api_type}' which is required for this task."
            ).format(
                api_type=APITypes.labels[APITypes.zrc],
            ),
            formset.non_form_errors(),
        )

    def test_multiple_orc(self):
        data = {
            "topic_name": "topic",
            "defaultservice_set-TOTAL_FORMS": 2,
            "callback": "bptl.tasks.tests.test_validate_required_services.task_2",
            "defaultservice_set-0-alias": "svc1",
            "defaultservice_set-0-service": self.orc1.pk,
            "defaultservice_set-1-alias": "other",
            "defaultservice_set-1-service": self.orc2.pk,
        }
        formset = DefaultServiceFormset(data={**MANAGEMENT_FORM, **data})

        result = formset.is_valid()

        self.assertTrue(result)
