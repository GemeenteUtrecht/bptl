from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from bptl.camunda.models import ExternalTask
from bptl.credentials.tests.factories import AppFactory, AppServiceCredentialsFactory
from bptl.tasks.base import MissingVariable
from bptl.tasks.tests.factories import DefaultServiceFactory, TaskMappingFactory
from bptl.tests.utils import mock_parallel, paginated_response
from bptl.work_units.zgw.objects.services import fetch_start_camunda_process_form
from bptl.work_units.zgw.objects.tests.utils import START_CAMUNDA_PROCESS_FORM_OBJ

from ..models import MetaObjectTypesConfig
from ..services import (
    fetch_review_request,
    fetch_reviews,
    get_review_request,
    get_reviews_for_review_request,
    update_review_request,
)
from .utils import (
    CATALOGI_ROOT,
    CATALOGUS,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    REVIEW_OBJECT,
    REVIEW_OBJECTTYPE,
    REVIEW_OBJECTTYPE_LATEST_VERSION,
    REVIEW_REQUEST_OBJECT,
    REVIEW_REQUEST_OBJECTTYPE,
    REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION,
    ZAAK_URL,
    ZAKEN_ROOT,
    AssignedUsersFactory,
    ReviewRequestFactory,
    ReviewsApprovalFactory,
    UserAssigneeFactory,
)

# class ObjectsServicesTests(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         super().setUpTestData()

#         cls.task_dict = {
#             "topic_name": "some-topic-name",
#             "worker_id": "test-worker-id",
#             "task_id": "test-task-id",
#             "variables": {
#                 "bptlAppId": serialize_variable("some-app-id"),
#             },
#         }
#         cls.task = ExternalTask.objects.create(
#             **cls.task_dict,
#         )
#         mapping = TaskMappingFactory.create(topic_name="some-topic-name")
#         DefaultServiceFactory.create(
#             task_mapping=mapping,
#             service__api_root=OBJECTS_ROOT,
#             service__api_type=APITypes.orc,
#             service__auth_type=AuthTypes.no_auth,
#             alias="objects",
#         )

#     @patch("bptl.work_units.zgw.objects.services.MetaObjectTypesConfig")
#     def test_wrongly_configured_meta_config(self, mock_meta_config):
#         mock_meta_config.start_camunda_process_form_objecttype = ""
#         with patch(
#             "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig.get_solo",
#             return_value=mock_meta_config,
#         ):
#             with self.assertRaises(RuntimeError):
#                 fetch_start_camunda_process_form(
#                     self.task, zaaktype_identificatie="", catalogus_domein=""
#                 )

#     @patch(
#         "bptl.work_units.zgw.objects.services.search_objects",
#         return_value=[paginated_response([]), {}],
#     )
#     @patch("bptl.work_units.zgw.objects.services.logger")
#     @patch("bptl.work_units.zgw.objects.services.MetaObjectTypesConfig")
#     def test_no_objects_found(self, mock_meta_config, mock_logger, mock_search_objects):
#         fetch_start_camunda_process_form(
#             self.task, zaaktype_identificatie="some-id", catalogus_domein="some-domein"
#         )
#         mock_logger.warning.assert_called_once()

#     @patch(
#         "bptl.work_units.zgw.objects.services.search_objects",
#         return_value=[paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ, 2]), {}],
#     )
#     @patch("bptl.work_units.zgw.objects.services.logger")
#     @patch(
#         "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
#     )
#     def test_more_than_one_objects_found(
#         self, mock_meta_config, mock_logger, mock_search_objects
#     ):
#         fetch_start_camunda_process_form(
#             self.task, zaaktype_identificatie="zaaktype", catalogus_domein="catalogus"
#         )
#         mock_logger.warning.assert_called_once()

#     @patch(
#         "bptl.work_units.zgw.objects.services.search_objects",
#         return_value=[paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]), {}],
#     )
#     @patch("bptl.work_units.zgw.objects.services.logger")
#     @patch(
#         "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
#     )
#     def test_success(self, mock_meta, mock_logger, mock_search_objects):
#         with patch(
#             "bptl.work_units.zgw.objects.services.MetaObjectTypesConfig",
#             side_effect=Exception,
#         ):
#             fetch_start_camunda_process_form(
#                 self.task,
#                 zaaktype_identificatie="zaaktype",
#                 catalogus_domein="catalogus",
#             )

#         mock_search_objects.assert_called_once()
#         mock_logger.warning.assert_not_called()


@requests_mock.Mocker()
class KownslObjectsServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        config = MetaObjectTypesConfig.get_solo()
        config.review_request_objecttype = REVIEW_REQUEST_OBJECTTYPE["url"]
        config.review_objecttype = REVIEW_OBJECTTYPE["url"]
        config.save()
        user_assignees = UserAssigneeFactory(
            **{
                "username": "some-user",
                "first_name": "Some Other First",
                "last_name": "Some Last",
                "full_name": "Some Other First Some Last",
            }
        )
        assigned_users2 = AssignedUsersFactory(
            **{
                "deadline": "2022-04-15",
                "user_assignees": [user_assignees],
                "group_assignees": [],
                "email_notification": False,
            }
        )
        cls.review_request = ReviewRequestFactory()
        cls.review_request["assignedUsers"].append(assigned_users2)

        cls.reviews_approval = ReviewsApprovalFactory()
        cls.task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "kownslUsers": serialize_variable(
                    ["user:some-user", "user:some-author"]
                ),
                "metadata": serialize_variable({"hihi": "hoho"}),
                "kownslReviewRequestId": serialize_variable(cls.review_request["id"]),
            },
        }
        cls.task = ExternalTask.objects.create(
            **cls.task_dict,
        )

        mapping = TaskMappingFactory.create(topic_name="some-topic-name")
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=OBJECTS_ROOT,
            service__api_type=APITypes.orc,
            service__auth_type=AuthTypes.no_auth,
            alias="objects",
        )
        DefaultServiceFactory.create(
            task_mapping=mapping,
            service__api_root=OBJECTTYPES_ROOT,
            service__api_type=APITypes.orc,
            service__auth_type=AuthTypes.no_auth,
            alias="objecttypes",
        )

    def test_fetch_review_request(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        with self.subTest("Zero objects returned."):
            with patch("bptl.work_units.zgw.objects.services.logger") as mock_logger:
                m.post(
                    f"{OBJECTS_ROOT}objects/search?pageSize=100",
                    json=paginated_response([]),
                )
                review_request = fetch_review_request(self.task)
            mock_logger.warning.assert_called_once_with(
                "No `{url}` object is found.".format(
                    url=REVIEW_REQUEST_OBJECTTYPE["url"]
                )
            )

        with self.subTest("One object returned."):
            m.post(
                f"{OBJECTS_ROOT}objects/search?pageSize=100",
                json=paginated_response([REVIEW_REQUEST_OBJECT]),
            )
            review_request = fetch_review_request(self.task)

        with self.subTest("Two objects returned."):
            with patch("bptl.work_units.zgw.objects.services.logger") as mock_logger:
                m.post(
                    f"{OBJECTS_ROOT}objects/search?pageSize=100",
                    json=paginated_response(
                        [REVIEW_REQUEST_OBJECT, REVIEW_REQUEST_OBJECT]
                    ),
                )
                review_request = fetch_review_request(self.task)
            mock_logger.warning.assert_called_once_with(
                "More than 1 `{url}` object is found.".format(
                    url=REVIEW_REQUEST_OBJECTTYPE["url"]
                )
            )

        self.assertEqual(review_request, REVIEW_REQUEST_OBJECT)

    def test_get_review_request(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([REVIEW_REQUEST_OBJECT]),
        )
        review_request = get_review_request(self.task)

        self.assertEqual(review_request, REVIEW_REQUEST_OBJECT["record"]["data"])

    def test_update_review_request(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([deepcopy(REVIEW_REQUEST_OBJECT)]),
        )
        m.patch(
            f"{OBJECTS_ROOT}objects/{REVIEW_REQUEST_OBJECT['uuid']}",
            json=REVIEW_REQUEST_OBJECT,
        )
        review_request = update_review_request(
            self.task, {"metadata": {"hihi": "hoho"}}
        )

        self.assertEqual(review_request, REVIEW_REQUEST_OBJECT["record"]["data"])

    def test_fetch_reviews(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([deepcopy(REVIEW_OBJECT)]),
        )
        reviews = fetch_reviews(
            self.task, review_request=REVIEW_REQUEST_OBJECT["record"]["data"]["id"]
        )
        self.assertEqual(reviews, [REVIEW_OBJECT])

    def test_get_reviews_for_review_request(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([deepcopy(REVIEW_OBJECT)]),
        )
        with patch(
            "bptl.work_units.zgw.objects.services.fetch_reviews"
        ) as patch_fetch_reviews:
            reviews = get_reviews_for_review_request(self.task)
        patch_fetch_reviews.assert_called_once_with(
            self.task, review_request=self.review_request["id"]
        )
