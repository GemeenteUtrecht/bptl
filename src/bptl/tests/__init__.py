from datetime import timezone as py_tz

import django.utils.timezone as dj_tz

if not hasattr(dj_tz, "utc"):
    dj_tz.utc = py_tz.utc
