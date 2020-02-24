from timeline_logger.models import TimelineLog


class DBLog:
    task = None

    def add(
        self,
        service: str,
        url: str,
        method: str,
        request_headers: dict,
        request_data: dict,
        response_status: int,
        response_headers: dict,
        response_data: dict,
        params: dict = None,
    ):

        extra_data = {
            "service_name": service,
            "request": {
                "url": url,
                "method": method,
                "headers": request_headers,
                "data": request_data,
                "params": params,
            },
            "response": {
                "status": response_status,
                "headers": response_headers,
                "data": response_data,
            },
        }
        TimelineLog.objects.create(content_object=self.task, extra_data=extra_data)
