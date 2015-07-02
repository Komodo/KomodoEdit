from __future__ import division, print_function, absolute_import

import logging
import bugsnag

class BugsnagHandler(logging.Handler, object):
    def __init__(self, api_key=None, extra_fields={}):
        super(BugsnagHandler, self).__init__()
        self.api_key = api_key
        self.extra_fields = extra_fields

    def emit(self, record):
        # Severity is not a one-to-one mapping, as there are only
        # a fixed number of severity levels available server side
        if record.levelname.lower() in ['error', 'critical']:
            severity = 'error'
        elif record.levelname.lower() in ['warning', 'info', 'debug']:
            return # KOMODO: Don't report warnings, info or debug messages
        else:
            severity = 'info'

        # Only extract a few specific fields, as we don't want to
        # repeat data already being sent over the wire (such as exc)
        record_fields = ['asctime', 'created', 'levelname', 'levelno', 'msecs',
            'name', 'process', 'processName', 'relativeCreated', 'thread',
            'threadName', ]

        extra_data = {}
        for field in record_fields:
            if hasattr(record, field):
                extra_data[field] = getattr(record, field)
        metadata = {"extra data":extra_data}
        for tab_name in self.extra_fields:
            metadata[tab_name] = {}
            for field_name in self.extra_fields[tab_name]:
                if hasattr(record, field_name):
                    metadata[tab_name][field_name] = getattr(record, field_name)

        api_key = self.api_key or bugsnag.configuration.api_key

        if record.exc_info:
            bugsnag.notify(record.exc_info, severity=severity, meta_data=metadata, api_key=api_key)
        else:
            # Create exception type dynamically, to prevent bugsnag.handlers
            # being prepended to the exception name due to class name
            # detection in utils. Because we are messing with the module
            # internals, we don't really want to expose this class anywhere
            level_name = record.levelname if record.levelname else "Message"
            exc_type = type('Log'+level_name, (Exception, ), {})
            exc = exc_type(record.getMessage())
            exc.__module__ = '__main__'

            bugsnag.notify(exc, severity=severity, meta_data=metadata)

