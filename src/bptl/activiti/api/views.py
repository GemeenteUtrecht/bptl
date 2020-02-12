from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import WorkUnitSerializer


class WorkUnitView(APIView):
    serializer = WorkUnitSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()

        # TODO perform task

        return Response(serializer.data, status=status.HTTP_201_CREATED)
