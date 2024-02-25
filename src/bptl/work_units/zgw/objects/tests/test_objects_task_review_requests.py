from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable

from bptl.camunda.models import ExternalTask
from bptl.tasks.base import MissingVariable

from ..tasks import (
    get_approval_status,
    get_approval_toelichtingen,
    get_review_request_start_process_information,
    get_review_response_status,
    lock_review_request,
    set_review_request_metadata,
)
from .utils import (
    REVIEW_REQUEST_OBJECT,
    AssignedUsersFactory,
    ReviewRequestFactory,
    ReviewsApprovalFactory,
    UserAssigneeFactory,
)


@requests_mock.Mocker()
class KownslTasktests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
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

    def test_missing_variables(self, m):
        task_dict = {
            "topic_name": "some-topic-name",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "bptlAppId": serialize_variable("some-app-id"),
            },
        }

        with self.subTest("get_approval_status"):
            task = ExternalTask.objects.create(
                **task_dict,
            )
            with self.assertRaises(MissingVariable) as exc:
                get_approval_status(task)
            self.assertEqual(
                exc.exception.args[0],
                "The variable kownslReviewRequestId is missing or empty.",
            )

        with self.subTest("get_review_response_status"):
            task = ExternalTask.objects.create(
                **task_dict,
            )
            with self.assertRaises(MissingVariable) as exc:
                get_review_response_status(task)

            self.assertEqual(
                exc.exception.args[0],
                "The variable kownslUsers is missing or empty.",
            )

            _task_dict = deepcopy(task_dict)
            _task_dict["variables"]["kownslUsers"] = serialize_variable("some-users")
            task = ExternalTask.objects.create(**_task_dict)
            with self.assertRaises(MissingVariable) as exc:
                get_review_response_status(task)
            self.assertEqual(
                exc.exception.args[0],
                "The variable kownslReviewRequestId is missing or empty.",
            )

        with self.subTest("get_review_request_start_process_information"):
            task = ExternalTask.objects.create(
                **task_dict,
            )
            with self.assertRaises(MissingVariable) as exc:
                get_review_request_start_process_information(task)
            self.assertEqual(
                exc.exception.args[0],
                "The variable kownslUsers is missing or empty.",
            )

            _task_dict = deepcopy(task_dict)
            _task_dict["variables"]["kownslUsers"] = serialize_variable("some-users")
            task = ExternalTask.objects.create(**_task_dict)
            with self.assertRaises(MissingVariable) as exc:
                get_review_request_start_process_information(task)
            self.assertEqual(
                exc.exception.args[0],
                "The variable kownslReviewRequestId is missing or empty.",
            )
        with self.subTest("set_review_request_metadata"):
            task = ExternalTask.objects.create(
                **task_dict,
            )
            with self.assertRaises(MissingVariable) as exc:
                set_review_request_metadata(task)
            self.assertEqual(
                exc.exception.args[0],
                "The variable metadata is missing or empty.",
            )

            _task_dict = deepcopy(task_dict)
            _task_dict["variables"]["metadata"] = serialize_variable(
                {"metadata": "some-id"}
            )
            task = ExternalTask.objects.create(**_task_dict)
            with self.assertRaises(MissingVariable) as exc:
                set_review_request_metadata(task)
            self.assertEqual(
                exc.exception.args[0],
                "The variable kownslReviewRequestId is missing or empty.",
            )
        with self.subTest("get_approval_toelichtingen"):
            task = ExternalTask.objects.create(
                **task_dict,
            )
            with self.assertRaises(MissingVariable) as exc:
                get_approval_toelichtingen(task)
            self.assertEqual(
                exc.exception.args[0],
                "The variable kownslReviewRequestId is missing or empty.",
            )

    def test_success_get_approval_status(self, m):
        task = ExternalTask.objects.create(
            **self.task_dict,
        )
        with patch(
            "bptl.work_units.zgw.objects.tasks.get_reviews_for_review_request",
            return_value=self.reviews_approval,
        ):
            result = get_approval_status(task)
        self.assertEqual(result["approvalResult"], True)

    def test_get_approval_status_no_reviews(self, m):
        task = ExternalTask.objects.create(
            **self.task_dict,
        )
        with patch(
            "bptl.work_units.zgw.objects.tasks.get_reviews_for_review_request",
            return_value=None,
        ):
            result = get_approval_status(task)
        self.assertEqual(result["approvalResult"], False)

    def test_get_review_response_status(self, m):
        task = ExternalTask.objects.create(
            **self.task_dict,
        )
        with patch(
            "bptl.work_units.zgw.objects.tasks.get_reviews_for_review_request",
            return_value=self.reviews_approval,
        ):
            result = get_review_response_status(task)
        self.assertEqual(result["remindThese"], ["user:some-user"])

    def test_get_review_response_status_no_reviews(self, m):
        task = ExternalTask.objects.create(
            **self.task_dict,
        )
        with patch(
            "bptl.work_units.zgw.objects.tasks.get_reviews_for_review_request",
            return_value=None,
        ):
            result = get_review_response_status(task)
        self.assertEqual(result["remindThese"], ["user:some-user", "user:some-author"])

    def test_get_review_request_start_process_information(self, m):
        task = ExternalTask.objects.create(
            **self.task_dict,
        )
        with patch(
            "bptl.work_units.zgw.objects.tasks.get_review_request",
            return_value=self.review_request,
        ):
            result = get_review_request_start_process_information(task)
        self.assertEqual(
            result,
            {
                "deadline": "2022-04-15",
                "reminderDate": "2022-04-14",
                "locked": False,
                "requester": "user:some-author",
                "reviewType": "advies",
            },
        )

    def test_set_review_request_metadata(self, m):
        task = ExternalTask.objects.create(
            **self.task_dict,
        )
        with patch(
            "bptl.work_units.zgw.objects.services.fetch_review_request",
            return_value=deepcopy(REVIEW_REQUEST_OBJECT),
        ):
            with patch(
                "bptl.work_units.zgw.objects.services.update_object_record_data",
                return_value=deepcopy(REVIEW_REQUEST_OBJECT),
            ):
                result = set_review_request_metadata(task)

        self.assertEqual(result, dict())

    def test_get_approval_toelichtingen(self, m):
        task = ExternalTask.objects.create(
            **self.task_dict,
        )
        with patch(
            "bptl.work_units.zgw.objects.tasks.get_reviews_for_review_request",
            return_value=self.reviews_approval,
        ):
            result = get_approval_toelichtingen(task)
        self.assertEqual(result, {"toelichtingen": "some-toelichting"})

    def test_get_approval_toelichtingen_no_reviews(self, m):
        task = ExternalTask.objects.create(
            **self.task_dict,
        )
        with patch(
            "bptl.work_units.zgw.objects.tasks.get_reviews_for_review_request",
            return_value=None,
        ):
            result = get_approval_toelichtingen(task)
        self.assertEqual(result, {"toelichtingen": ""})

    def test_set_review_request_metadata(self, m):
        task = ExternalTask.objects.create(
            **self.task_dict,
        )
        with patch(
            "bptl.work_units.zgw.objects.services.fetch_review_request",
            return_value=deepcopy(REVIEW_REQUEST_OBJECT),
        ):
            with patch(
                "bptl.work_units.zgw.objects.services.update_object_record_data",
                return_value=deepcopy(REVIEW_REQUEST_OBJECT),
            ) as mock_update_object_record_data:
                result = lock_review_request(task)

        mock_update_object_record_data.assert_called_once_with(
            task,
            {
                "url": REVIEW_REQUEST_OBJECT["url"],
                "uuid": REVIEW_REQUEST_OBJECT["uuid"],
                "type": REVIEW_REQUEST_OBJECT["type"],
                "record": {
                    "index": REVIEW_REQUEST_OBJECT["record"]["index"],
                    "typeVersion": REVIEW_REQUEST_OBJECT["record"]["typeVersion"],
                    "data": {
                        "created": REVIEW_REQUEST_OBJECT["record"]["data"]["created"],
                        "documents": REVIEW_REQUEST_OBJECT["record"]["data"][
                            "documents"
                        ],
                        "id": REVIEW_REQUEST_OBJECT["record"]["data"]["id"],
                        "locked": True,
                        "lockReason": "Alle verzoeken zijn uitgevoerd.",
                        "metadata": REVIEW_REQUEST_OBJECT["record"]["data"]["metadata"],
                        "requester": REVIEW_REQUEST_OBJECT["record"]["data"][
                            "requester"
                        ],
                        "toelichting": REVIEW_REQUEST_OBJECT["record"]["data"][
                            "toelichting"
                        ],
                        "zaak": REVIEW_REQUEST_OBJECT["record"]["data"]["zaak"],
                        "zaakeigenschappen": [],
                        "assignedUsers": REVIEW_REQUEST_OBJECT["record"]["data"][
                            "assignedUsers"
                        ],
                        "isBeingReconfigured": REVIEW_REQUEST_OBJECT["record"]["data"][
                            "isBeingReconfigured"
                        ],
                        "numReviewsGivenBeforeChange": REVIEW_REQUEST_OBJECT["record"][
                            "data"
                        ]["numReviewsGivenBeforeChange"],
                        "reviewType": REVIEW_REQUEST_OBJECT["record"]["data"][
                            "reviewType"
                        ],
                        "userDeadlines": REVIEW_REQUEST_OBJECT["record"]["data"][
                            "userDeadlines"
                        ],
                    },
                    "geometry": REVIEW_REQUEST_OBJECT["record"]["geometry"],
                    "startAt": REVIEW_REQUEST_OBJECT["record"]["startAt"],
                    "endAt": REVIEW_REQUEST_OBJECT["record"]["endAt"],
                    "registrationAt": REVIEW_REQUEST_OBJECT["record"]["registrationAt"],
                    "correctionFor": REVIEW_REQUEST_OBJECT["record"]["correctionFor"],
                    "correctedBy": "None",
                },
            },
            {
                "created": REVIEW_REQUEST_OBJECT["record"]["data"]["created"],
                "documents": REVIEW_REQUEST_OBJECT["record"]["data"]["documents"],
                "id": REVIEW_REQUEST_OBJECT["record"]["data"]["id"],
                "locked": True,
                "lockReason": "Alle verzoeken zijn uitgevoerd.",
                "metadata": REVIEW_REQUEST_OBJECT["record"]["data"]["metadata"],
                "requester": REVIEW_REQUEST_OBJECT["record"]["data"]["requester"],
                "toelichting": REVIEW_REQUEST_OBJECT["record"]["data"]["toelichting"],
                "zaak": REVIEW_REQUEST_OBJECT["record"]["data"]["zaak"],
                "zaakeigenschappen": [],
                "assignedUsers": REVIEW_REQUEST_OBJECT["record"]["data"][
                    "assignedUsers"
                ],
                "isBeingReconfigured": REVIEW_REQUEST_OBJECT["record"]["data"][
                    "isBeingReconfigured"
                ],
                "numReviewsGivenBeforeChange": REVIEW_REQUEST_OBJECT["record"]["data"][
                    "numReviewsGivenBeforeChange"
                ],
                "reviewType": REVIEW_REQUEST_OBJECT["record"]["data"]["reviewType"],
                "userDeadlines": REVIEW_REQUEST_OBJECT["record"]["data"][
                    "userDeadlines"
                ],
            },
            username=None,
        )

        self.assertEqual(result, dict())
