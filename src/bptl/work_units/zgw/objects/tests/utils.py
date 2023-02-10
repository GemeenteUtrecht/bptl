CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
OBJECTTYPES_ROOT = "http://objecttype.nl/api/v1/"
OBJECTS_ROOT = "http://object.nl/api/v1/"
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
