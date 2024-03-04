from copy import deepcopy

import factory

from ..constants import KownslTypes

ZAKEN_ROOT = "https://zaken.nl/"
DOCUMENTS_ROOT = "https://drc.nl/"
CATALOGI_ROOT = "http://ztc.nl/"
OBJECTTYPES_ROOT = "http://objecttype.nl/api/v1/"
OBJECTS_ROOT = "http://object.nl/api/v2/"

DOCUMENT_URL = f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/30e4deca-29ca-4798-bab1-3ad75cf29c30"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/0c79c41d-72ef-4ea2-8c4c-03c9945da2a2"

CATALOGUS = f"{CATALOGI_ROOT}catalogussen/7022a89e-0dd1-4074-9c3a-1a990e6c18ab"
BRONORGANISATIE = "123456789"
IDENTIFICATIE = "ZAAK-0000001"
RR_ID = "14aec7a0-06de-4b55-b839-a1c9a0415b46"
PI_URL = "https://camunda.example.com/engine-rest/process-instance"


START_CAMUNDA_PROCESS_FORM_OT = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/1",
    "name": "StartCamundaProcessForm",
    "namePlural": "StartCamundaProcessForms",
    "description": "",
    "data_classification": "",
    "maintainer_organization": "",
    "maintainer_department": "",
    "contact_person": "",
    "contact_email": "",
    "source": "",
    "update_frequency": "",
    "provider_organization": "",
    "documentation_url": "",
    "labels": {},
    "created_at": "2019-08-24",
    "modified_at": "2019-08-24",
    "versions": [],
}


PROCESS_ROL = {
    "label": "Some Rol",
    "order": 1,
    "required": True,
    "betrokkeneType": "medewerker",
    "roltypeOmschrijving": "Some Rol",
}

PROCESS_EIGENSCHAP = {
    "label": "Some Eigenschap 1",
    "order": 1,
    "default": "",
    "required": True,
    "eigenschapnaam": "Some Eigenschap 1",
}


PROCESS_INFORMATIE_OBJECT = {
    "label": "Some Document",
    "order": 1,
    "required": True,
    "allowMultiple": True,
    "informatieobjecttypeOmschrijving": "SomeDocument",
}

START_CAMUNDA_PROCESS_FORM = {
    "processRollen": [PROCESS_ROL],
    "zaaktypeCatalogus": "SOME-DOMEIN",
    "processEigenschappen": [PROCESS_EIGENSCHAP],
    "zaaktypeIdentificaties": ["1"],
    "processInformatieObjecten": [PROCESS_INFORMATIE_OBJECT],
    "camundaProcessDefinitionKey": "some_definition_key",
}


START_CAMUNDA_PROCESS_FORM_OBJ = {
    "url": f"{OBJECTS_ROOT}objects/e0346ea0-75aa-47e0-9283-cfb35963b725",
    "type": START_CAMUNDA_PROCESS_FORM_OT["url"],
    "record": {
        "index": 1,
        "typeVersion": 1,
        "data": START_CAMUNDA_PROCESS_FORM,
        "geometry": {},
        "startAt": "2021-07-09",
        "endAt": None,
        "registrationAt": "2021-07-09",
        "correctionFor": None,
        "correctedBy": None,
    },
}

CHECKLISTTYPE_OBJECTTYPE = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/4",
    "version": 4,
    "objectType": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
    "status": "published",
    "jsonSchema": {
        "type": "object",
        "title": "ChecklistType",
        "required": [
            "zaaktypeCatalogus",
            "zaaktypeIdentificaties",
            "questions",
        ],
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "title": "ChecklistQuestion",
                    "required": ["question", "choices", "order"],
                    "properties": {
                        "order": {"type": "integer"},
                        "choices": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "naam": {"type": "string"},
                                    "waarde": {"type": "string"},
                                },
                            },
                        },
                        "question": {"type": "string"},
                    },
                },
            },
            "zaaktypeCatalogus": {"type": "string"},
            "zaaktypeIdentificaties": {"type": "array", "items": {"type": "string"}},
        },
    },
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "publishedAt": "1999-12-31",
}

CHECKLISTTYPE_OBJECT = {
    "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
    "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
    "type": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
    "record": {
        "index": 1,
        "typeVersion": 4,
        "data": {
            "zaaktypeCatalogus": "UTRE",
            "zaaktypeIdentificaties": ["ZT1"],
            "questions": [
                {
                    "choices": [{"name": "Ja", "value": "Ja"}],
                    "question": "Ja?",
                    "order": 1,
                },
                {
                    "choices": [{"name": "Nee", "value": "Nee"}],
                    "question": "Nee?",
                    "order": 2,
                },
            ],
        },
        "geometry": "None",
        "startAt": "1999-12-31",
        "endAt": "None",
        "registrationAt": "1999-12-31",
        "correctionFor": "None",
        "correctedBy": "None",
    },
}

CHECKLIST_OBJECTTYPE = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
    "uuid": "5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
    "name": "Checklist",
    "namePlural": "Checklists",
    "description": "Describes the json schema of a checklist",
    "dataClassification": "open",
    "maintainerOrganization": "",
    "maintainerDepartment": "",
    "contactPerson": "",
    "contactEmail": "",
    "source": "",
    "updateFrequency": "unknown",
    "providerOrganization": "",
    "documentationUrl": "",
    "labels": {},
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "versions": [
        f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4/versions/3",
        f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4/versions/2",
        f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4/versions/1",
    ],
}
CHECKLIST_OBJECTTYPE_LATEST_VERSION = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4/versions/3",
    "version": 3,
    "objectType": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
    "status": "published",
    "jsonSchema": {
        "type": "object",
        "title": "Checklist",
        "required": ["answers", "zaak", "locked"],
        "properties": {
            "zaak": {"type": "string"},
            "locked": {"type": "boolean"},
            "answers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "title": "ChecklistAnswer",
                    "required": ["question", "answer"],
                    "properties": {
                        "answer": {"type": "string"},
                        "remarks": {"type": "string"},
                        "document": {"type": "string"},
                        "question": {"type": "string"},
                        "userAssignee": {"type": ["string", "null"]},
                        "groupAssignee": {"type": ["string", "null"]},
                    },
                },
            },
        },
    },
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "publishedAt": "1999-12-31",
}

CHECKLIST_OBJECT = {
    "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
    "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
    "type": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
    "record": {
        "index": 1,
        "typeVersion": 3,
        "data": {
            "zaak": ZAAK_URL,
            "answers": [
                {"answer": "Ja", "question": "Ja?"},
                {"answer": "Nee", "question": "Nee?"},
            ],
            "locked": False,
        },
        "geometry": "None",
        "startAt": "1999-12-31",
        "endAt": "None",
        "registrationAt": "1999-12-31",
        "correctionFor": "None",
        "correctedBy": "None",
    },
}


class UserAssigneeFactory(factory.DictFactory):
    email = "some-author@email.zac"
    first_name = "Some First"
    full_name = "Some First Some Last"
    username = "some-author"
    last_name = "Some Last"

    class Meta:
        rename = {
            "first_name": "firstName",
            "last_name": "lastName",
            "full_name": "fullName",
        }


class AssignedUsersFactory(factory.DictFactory):
    deadline = "2022-04-14"
    user_assignees = factory.List([factory.SubFactory(UserAssigneeFactory)])
    group_assignees = factory.List([])
    email_notification = False

    class Meta:
        rename = {
            "user_assignees": "userAssignees",
            "email_notification": "emailNotification",
        }


class MetaDataFactory(factory.DictFactory):
    task_definition_id = "submitAdvice"
    process_instance_id = "6ebf534a-bc0a-11ec-a591-c69dd6a420a0"

    class Meta:
        rename = {
            "task_definition_id": "taskDefinitionId",
            "process_instance_id": "processInstanceId",
        }


class ReviewRequestFactory(factory.DictFactory):
    assigned_users = factory.List([factory.SubFactory(AssignedUsersFactory)])
    created = "2022-04-14T15:49:09.830235Z"
    documents = factory.List([])
    id = deepcopy(RR_ID)
    is_being_reconfigured = False
    locked = False
    lockReason = ""
    metadata = factory.SubFactory(MetaDataFactory)
    num_reviews_given_before_change = 0
    requester = factory.SubFactory(UserAssigneeFactory)
    review_type = KownslTypes.advice
    toelichting = "some-toelichting"
    user_deadlines = factory.Dict(
        {
            "user:some-author": "2022-04-14",
            "user:some-user": "2022-04-15",
        }
    )
    zaak = deepcopy(ZAAK_URL)
    zaakeigenschappen = factory.List([])

    class Meta:
        rename = {
            "assigned_users": "assignedUsers",
            "is_being_reconfigured": "isBeingReconfigured",
            "num_reviews_given_before_change": "numReviewsGivenBeforeChange",
            "review_type": "reviewType",
            "user_deadlines": "userDeadlines",
        }


class ReviewDocumentFactory(factory.DictFactory):
    document = deepcopy(DOCUMENT_URL) + "?versie=1"
    source_version = 1
    review_version = 2

    class Meta:
        rename = {"source_version": "sourceVersion", "review_version": "reviewVersion"}


class KownslZaakEigenschapFactory(factory.DictFactory):
    url = f"{ZAAK_URL}zaakeigenschappen/c0524527-3539-4313-8c00-41358069e65b"
    naam = "SomeEigenschap"
    waarde = "SomeWaarde"


class AdviceFactory(factory.DictFactory):
    author = factory.SubFactory(UserAssigneeFactory)
    advice = "some-advice"
    created = "2022-04-14T15:50:09.830235Z"
    group = factory.Dict(dict())
    review_documents = factory.List([factory.SubFactory(ReviewDocumentFactory)])
    zaakeigenschappen = factory.List([factory.SubFactory(KownslZaakEigenschapFactory)])

    class Meta:
        rename = {
            "review_documents": "reviewDocuments",
        }


class ApprovalFactory(factory.DictFactory):
    author = factory.SubFactory(UserAssigneeFactory)
    approved = True
    created = "2022-04-14T15:51:09.830235Z"
    group = factory.Dict(dict())
    review_documents = factory.List([factory.SubFactory(ReviewDocumentFactory)])
    toelichting = "some-toelichting"
    zaakeigenschappen = factory.List([factory.SubFactory(KownslZaakEigenschapFactory)])

    class Meta:
        rename = {
            "review_documents": "reviewDocuments",
        }


class ReviewsFactory(factory.DictFactory):
    id = "6a9a169e-aa6f-4dd7-bbea-6bedea74c456"
    requester = factory.SubFactory(UserAssigneeFactory)
    reviews = factory.List([factory.SubFactory(AdviceFactory)])
    review_request = deepcopy(RR_ID)
    review_type = KownslTypes.advice
    zaak = deepcopy(ZAAK_URL)

    class Meta:
        rename = {
            "review_request": "reviewRequest",
            "review_type": "reviewType",
        }


class ReviewsApprovalFactory(factory.DictFactory):
    id = "6a9a169e-aa6f-4dd7-bbea-6bedea74c457"
    requester = factory.SubFactory(UserAssigneeFactory)
    reviews = factory.List([factory.SubFactory(ApprovalFactory)])
    review_request = deepcopy(RR_ID)
    revtest_get_review_request_start_process_informationiew_type = KownslTypes.approval
    zaak = deepcopy(ZAAK_URL)

    class Meta:
        rename = {
            "review_request": "reviewRequest",
            "review_type": "reviewType",
        }


REVIEW_REQUEST_OBJECTTYPE = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
    "uuid": "b4ec3f47-bc20-4872-955c-cb5f67646eae",
    "name": "ReviewRequest",
    "namePlural": "ReviewRequests",
    "description": "Describes the json schema of a review request.",
    "dataClassification": "open",
    "maintainerOrganization": "",
    "maintainerDepartment": "",
    "contactPerson": "",
    "contactEmail": "",
    "source": "",
    "updateFrequency": "unknown",
    "providerOrganization": "",
    "documentationUrl": "",
    "labels": dict(),
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "versions": [
        f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/4",
        f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/3",
        f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/2",
        f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/1",
    ],
}


REVIEW_REQUEST_OBJECTTYPE_LATEST_VERSION = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae/versions/4",
    "version": 4,
    "objectType": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646eae",
    "status": "published",
    "jsonSchema": {
        "type": "object",
        "$defs": {
            "user": {
                "type": "object",
                "title": "user",
                "required": [
                    "username",
                    "firstName",
                    "fullName",
                    "lastName",
                    "email",
                ],
                "properties": {
                    "email": {"type": "string"},
                    "fullName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "username": {"type": "string"},
                    "firstName": {"type": "string"},
                },
            },
            "group": {
                "type": "object",
                "title": "group",
                "required": ["name", "fullName"],
                "properties": {
                    "name": {"type": "string"},
                    "fullName": {"type": "string"},
                },
            },
            "assignedUser": {
                "type": "object",
                "title": "AssignedUser",
                "required": [
                    "deadline",
                    "emailNotification",
                    "userAssignees",
                    "groupAssignees",
                ],
                "properties": {
                    "deadline": {"type": "string"},
                    "userAssignees": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/user"},
                    },
                    "groupAssignees": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/group"},
                    },
                    "emailNotification": {"type": "boolean"},
                },
            },
        },
        "title": "ReviewRequest",
        "required": [
            "assignedUsers",
            "created",
            "documents",
            "id",
            "isBeingReconfigured",
            "locked",
            "lockReason",
            "meta",
            "metadata",
            "numReviewsGivenBeforeChange",
            "requester",
            "reviewType",
            "toelichting",
            "userDeadlines",
            "zaak",
        ],
        "properties": {
            "id": {"type": "string"},
            "zaak": {"type": "string"},
            "locked": {"type": "boolean"},
            "created": {"type": "string"},
            "metadata": {
                "type": "object",
                "title": "Metadata",
                "properties": {
                    "taskDefinitionId": {"type": "string"},
                    "processInstanceId": {"type": "string"},
                },
            },
            "documents": {"type": "array", "items": {"type": "string"}},
            "requester": {"$ref": "#/$defs/user"},
            "lockReason": {"type": "string"},
            "reviewType": {"type": "string"},
            "toelichting": {"type": "string"},
            "assignedUsers": {
                "type": "array",
                "items": {"$ref": "#/$defs/assignedUser"},
            },
            "userDeadlines": {"type": "object"},
            "isBeingReconfigured": {"type": "boolean"},
            "numReviewsGivenBeforeChange": {"type": "integer"},
        },
    },
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "publishedAt": "1999-12-31",
}

REVIEW_REQUEST_OBJECT = {
    "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
    "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
    "type": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646ead",
    "record": {
        "index": 1,
        "typeVersion": 4,
        "data": ReviewRequestFactory(),
        "geometry": "None",
        "startAt": "1999-12-31",
        "endAt": "None",
        "registrationAt": "1999-12-31",
        "correctionFor": "None",
        "correctedBy": "None",
    },
}

REVIEW_OBJECTTYPE = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646ead",
    "uuid": "b4ec3f47-bc20-4872-955c-cb5f67646ead",
    "name": "Review",
    "namePlural": "Reviews",
    "description": "Describes the json schema of a review.",
    "dataClassification": "open",
    "maintainerOrganization": "",
    "maintainerDepartment": "",
    "contactPerson": "",
    "contactEmail": "",
    "source": "",
    "updateFrequency": "unknown",
    "providerOrganization": "",
    "documentationUrl": "",
    "labels": dict(),
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "versions": [
        f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead/versions/4",
        f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead/versions/3",
        f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead/versions/2",
        f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead/versions/1",
    ],
}


REVIEW_OBJECTTYPE_LATEST_VERSION = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/b4ec3f47-bc20-4872-955c-cb5f67646ead/versions/4",
    "version": 4,
    "objectType": f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead",
    "status": "published",
    "jsonSchema": {
        "type": "object",
        "$defs": {
            "id": {"type": "string"},
            "user": {
                "type": "object",
                "title": "user",
                "required": ["username", "firstName", "fullName", "lastName", "email"],
                "properties": {
                    "email": {"type": "string"},
                    "fullName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "username": {"type": "string"},
                    "firstName": {"type": "string"},
                },
            },
            "zaak": {"type": "string"},
            "group": {
                "type": "object",
                "title": "group",
                "required": ["name", "fullName"],
                "properties": {
                    "name": {"type": "string"},
                    "fullName": {"type": "string"},
                },
            },
            "advice": {
                "type": "object",
                "title": "Advice",
                "required": ["advice", "author", "created"],
                "properties": {
                    "group": {"$ref": "#/$defs/group"},
                    "advice": {"type": "string"},
                    "author": {"$ref": "#/$defs/user"},
                    "created": {"$ref": "#/$defs/created"},
                    "reviewDocuments": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/reviewDocument"},
                    },
                    "zaakeigenschappen": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/zaakeigenschap"},
                    },
                },
            },
            "created": {"type": "string"},
            "approval": {
                "name": "Approval",
                "type": "object",
                "required": ["approved", "author", "created", "toelichting"],
                "properties": {
                    "group": {"$ref": "#/$defs/group"},
                    "author": {"$ref": "#/$defs/user"},
                    "created": {"$ref": "#/$defs/created"},
                    "approved": {"type": "boolean"},
                    "toelichting": {"type": "string"},
                    "reviewDocuments": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/reviewDocument"},
                    },
                    "zaakeigenschappen": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/zaakeigenschap"},
                    },
                },
            },
            "reviewType": {"type": "string"},
            "reviewRequest": {"type": "string"},
            "reviewDocument": {
                "type": "object",
                "title": "reviewDocument",
                "required": ["document", "sourceVersion", "reviewVersion"],
                "properties": {
                    "document": {"type": "string"},
                    "reviewVersion": {"type": "string"},
                    "sourceVersion": {"type": "string"},
                },
            },
            "zaakeigenschap": {
                "type": "object",
                "title": "zaakeigenschap",
                "required": ["url", "naam", "waarde"],
                "properties": {
                    "url": {"type": "string"},
                    "naam": {"type": "string"},
                    "waarde": {"type": "string"},
                },
            },
        },
        "title": "Reviews",
        "required": [
            "id",
            "requester",
            "reviewRequest",
            "reviewType",
            "reviews",
            "zaak",
        ],
        "properties": {
            "id": {"$ref": "#/$defs/id"},
            "zaak": {"$ref": "#/$defs/zaak"},
            "reviews": {
                "type": "array",
                "items": {
                    "oneOf": [{"$ref": "#/$defs/advice"}, {"$ref": "#/$defs/approval"}]
                },
            },
            "requester": {"$ref": "#/$defs/user"},
            "reviewType": {"$ref": "#/$defs/reviewType"},
            "reviewRequest": {"$ref": "#/$defs/reviewRequest"},
        },
    },
    "createdAt": "1999-12-31",
    "modifiedAt": "1999-12-31",
    "publishedAt": "1999-12-31",
}

REVIEW_OBJECT = {
    "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
    "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
    "type": f"{OBJECTTYPES_ROOT}objecttypes/b3ec3f47-bc20-4872-955c-cb5f67646ead",
    "record": {
        "index": 1,
        "typeVersion": 4,
        "data": {},
        "geometry": "None",
        "startAt": "1999-12-31",
        "endAt": "None",
        "registrationAt": "1999-12-31",
        "correctionFor": "None",
        "correctedBy": "None",
    },
}
