from __future__ import division, print_function, absolute_import

from distutils.sysconfig import get_python_lib
import threading
import os
import socket

from bugsnag.utils import fully_qualified_class_name
from bugsnag.middleware import MiddlewareStack, DefaultMiddleware


threadlocal = threading.local()

class _BaseConfiguration(object):
    def get(self, name, overrides=None):
        """
        Get a single configuration option, using values from overrides
        first if they exist.
        """
        if overrides:
            return overrides.get(name, getattr(self, name))
        else:
            return getattr(self, name)

    def configure(self, **options):
        """
        Set one or more configuration settings.
        """
        for name, value in options.items():
            setattr(self, name, value)

        return self


class Configuration(_BaseConfiguration):
    """
    Global app-level Bugsnag configuration settings.
    """
    def __init__(self):
        self.api_key = os.environ.get('BUGSNAG_API_KEY', None)
        self.release_stage = os.environ.get("BUGSNAG_RELEASE_STAGE", "production")
        self.notify_release_stages = None
        self.auto_notify = True
        self.send_code = True
        self.use_ssl = True
        self.lib_root = get_python_lib()
        self.project_root = os.getcwd()
        self.app_version = None
        self.params_filters = ["password", "password_confirmation", "cookie", "authorization"]
        self.ignore_classes = ["KeyboardInterrupt", "django.http.Http404"]
        self.endpoint = "notify.bugsnag.com"
        self.traceback_exclude_modules = []

        self.middleware = MiddlewareStack()
        self.middleware.append(DefaultMiddleware)

        if not os.getenv("DYNO"):
            self.hostname = socket.gethostname()
        else:
            self.hostname = None

    def should_notify(self):
        return self.notify_release_stages is None or \
            self.release_stage in self.notify_release_stages

    def should_ignore(self, exception):
        return self.ignore_classes is not None and \
            fully_qualified_class_name(exception) in self.ignore_classes

    def get_endpoint(self):
        proto = "https" if self.use_ssl else "http"
        return "%s://%s" % (proto, self.endpoint)

class RequestConfiguration(_BaseConfiguration):
    """
    Per-request Bugsnag configuration settings.
    """

    @classmethod
    def get_instance(cls):
        """
        Get this thread's instance of the RequestConfiguration.
        """
        instance = getattr(threadlocal, "bugsnag", None)
        if not instance:
            instance = RequestConfiguration()
            setattr(threadlocal, "bugsnag", instance)

        return instance

    @classmethod
    def clear(cls):
        """
        Clear this thread's instance of the RequestConfiguration.
        """
        if hasattr(threadlocal, "bugsnag"):
            delattr(threadlocal, "bugsnag")

    def __init__(self):
        self.context = None
        self.grouping_hash = None
        self.user = {}
        self.meta_data = {}

        # legacy fields
        self.user_id = None
        self.extra_data = {}
        self.request_data = {}
        self.environment_data = {}
        self.session_data = {}
