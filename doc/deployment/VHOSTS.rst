Apache + mod-wsgi configuration
===============================

An example Apache2 vhost configuration follows::

    WSGIDaemonProcess camunda_worker-<target> threads=5 maximum-requests=1000 user=<user> group=staff
    WSGIRestrictStdout Off

    <VirtualHost *:80>
        ServerName my.domain.name

        ErrorLog "/srv/sites/camunda_worker/log/apache2/error.log"
        CustomLog "/srv/sites/camunda_worker/log/apache2/access.log" common

        WSGIProcessGroup camunda_worker-<target>

        Alias /media "/srv/sites/camunda_worker/media/"
        Alias /static "/srv/sites/camunda_worker/static/"

        WSGIScriptAlias / "/srv/sites/camunda_worker/src/camunda_worker/wsgi/wsgi_<target>.py"
    </VirtualHost>


Nginx + uwsgi + supervisor configuration
========================================

Supervisor/uwsgi:
-----------------

.. code::

    [program:uwsgi-camunda_worker-<target>]
    user = <user>
    command = /srv/sites/camunda_worker/env/bin/uwsgi --socket 127.0.0.1:8001 --wsgi-file /srv/sites/camunda_worker/src/camunda_worker/wsgi/wsgi_<target>.py
    home = /srv/sites/camunda_worker/env
    master = true
    processes = 8
    harakiri = 600
    autostart = true
    autorestart = true
    stderr_logfile = /srv/sites/camunda_worker/log/uwsgi_err.log
    stdout_logfile = /srv/sites/camunda_worker/log/uwsgi_out.log
    stopsignal = QUIT

Nginx
-----

.. code::

    upstream django_camunda_worker_<target> {
      ip_hash;
      server 127.0.0.1:8001;
    }

    server {
      listen :80;
      server_name  my.domain.name;

      access_log /srv/sites/camunda_worker/log/nginx-access.log;
      error_log /srv/sites/camunda_worker/log/nginx-error.log;

      location /500.html {
        root /srv/sites/camunda_worker/src/camunda_worker/templates/;
      }
      error_page 500 502 503 504 /500.html;

      location /static/ {
        alias /srv/sites/camunda_worker/static/;
        expires 30d;
      }

      location /media/ {
        alias /srv/sites/camunda_worker/media/;
        expires 30d;
      }

      location / {
        uwsgi_pass django_camunda_worker_<target>;
      }
    }
