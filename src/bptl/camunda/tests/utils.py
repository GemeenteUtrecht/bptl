def get_fetch_and_lock_response(topic="createOrder", variables=None):
    return [
        {
            "activityId": "anActivityId",
            "activityInstanceId": "anActivityInstanceId",
            "errorMessage": "anErrorMessage",
            "errorDetails": "anErrorDetails",
            "executionId": "anExecutionId",
            "id": "anExternalTaskId",
            "lockExpirationTime": "2025-10-06T16:34:42.00+0200",
            "processDefinitionId": "aProcessDefinitionId",
            "processDefinitionKey": "aProcessDefinitionKey",
            "processInstanceId": "aProcessInstanceId",
            "tenantId": "tenantOne",
            "retries": 3,
            "workerId": "aWorkerId",
            "priority": 4,
            "topicName": topic,
            "businessKey": "aBusinessKey",
            "variables": variables or {},
        }
    ]
