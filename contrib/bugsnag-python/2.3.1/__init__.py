import sys
import traceback

from bugsnag.configuration import Configuration, RequestConfiguration
from bugsnag.notification import Notification

configuration = Configuration()

def configure(**options):
    """
    Configure the Bugsnag notifier application-wide settings.
    """
    configuration.configure(**options)


def configure_request(**options):
    """
    Configure the Bugsnag notifier per-request settings.
    """
    RequestConfiguration.get_instance().configure(**options)

def add_metadata_tab(tab_name, data):
    """
    Add metaData to the tab

    bugsnag.add_metadata_tab("user", {"id": "1", "name": "Conrad"})
    """
    meta_data = RequestConfiguration.get_instance().meta_data
    if not tab_name in meta_data:
        meta_data[tab_name] = {}

    meta_data[tab_name].update(data)

def clear_request_config():
    """
    Clears the per-request settings.
    """
    RequestConfiguration.clear()


def notify(exception, **options):
    """
    Notify bugsnag of an exception.
    """
    try:
        if isinstance(exception, (list, tuple)):
            # Exception tuples, eg. from sys.exc_info
            if not "traceback" in options:
                options["traceback"] = exception[2]

            Notification(exception[1], configuration,
                        RequestConfiguration.get_instance(), **options).deliver()
        else:
            # Exception objects
            Notification(exception, configuration,
                        RequestConfiguration.get_instance(), **options).deliver()
    except Exception:
        try:
            log("Notification failed")
            print((traceback.format_exc()))
        except Exception:
            print(("[BUGSNAG] error in exception handler"))
            print((traceback.format_exc()))

def auto_notify(exception, **options):
    """
    Notify bugsnag of an exception if auto_notify is enabled.
    """
    if configuration.auto_notify:
        notify(exception, severity="error", **options)

def before_notify(callback):
    """
    Add a callback to be called before bugsnag is notified

    This can be used to alter the notification before sending it to Bugsnag.
    """
    configuration.middleware.before_notify(callback)

def log(message):
    """
    Print a log message with a Bugsnag prefix.
    """
    print(("** [Bugsnag] %s" % message))


def warn(message):
    """
    Print a warning message with a Bugsnag prefix.
    """
    sys.stderr.write("** [Bugsnag] WARNING: %s\n" % message)


# Hook into all uncaught exceptions
def __bugsnag_excepthook(exctype, exception, traceback):
    try:
        auto_notify(exception, traceback=traceback)
    except:
        print(("[BUGSNAG] Error in excepthook, probably shutting down."))
        pass

    _old_excepthook(exctype, exception, traceback)

_old_excepthook = sys.excepthook
sys.excepthook = __bugsnag_excepthook
