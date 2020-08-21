from djangorestframework_camel_case.parser import CamelCaseJSONParser
from rest_framework import permissions, status, views
from rest_framework.request import Request
from rest_framework.response import Response

from .authentication import ValidSignAuthentication
from .handlers import on_package_complete
from .serializers import CallbackSerializer, EventTypes


class CallbackView(views.APIView):
    authentication_classes = (ValidSignAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (CamelCaseJSONParser,)

    def post(self, request: Request):
        serializer = CallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data["name"] == EventTypes.PACKAGE_COMPLETE:
            on_package_complete(serializer.validated_data["package_id"])

        return Response(status=status.HTTP_204_NO_CONTENT)
