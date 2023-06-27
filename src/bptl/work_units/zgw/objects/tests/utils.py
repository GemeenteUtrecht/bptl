CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS = f"{CATALOGI_ROOT}catalogussen/7022a89e-0dd1-4074-9c3a-1a990e6c18ab"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
OBJECTTYPES_ROOT = "http://objecttype.nl/api/v1/"
OBJECTS_ROOT = "http://object.nl/api/v2/"
PI_URL = "https://camunda.example.com/engine-rest/process-instance"
BRONORGANISATIE = "123456789"
IDENTIFICATIE = "ZAAK-0000001"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7"


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
            "meta",
        ],
        "properties": {
            "meta": True,
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
            "meta": True,
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
        "required": ["answers", "zaak", "meta"],
        "properties": {
            "meta": True,
            "zaak": {"type": "string"},
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
            "meta": True,
            "zaak": ZAAK_URL,
            "answers": [
                {"answer": "Ja", "question": "Ja?"},
                {"answer": "Nee", "question": "Nee?"},
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
