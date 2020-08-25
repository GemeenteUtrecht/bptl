import threading


class RequestAdminMixin:
    def __init__(self, *args, **kwargs):
        self._request_local = threading.local()
        self._request_local.request = None
        super().__init__(*args, **kwargs)

    def get_request(self):
        return self._request_local.request

    def set_request(self, request):
        self._request_local.request = request

    def changeform_view(self, request, *args, **kwargs):
        # stash the request
        self.set_request(request)
        return super().changeform_view(request, *args, **kwargs)
