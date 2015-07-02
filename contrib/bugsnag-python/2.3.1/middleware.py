import bugsnag

class SimpleMiddleware(object):
    def __init__(self, before=None, after=None):
        self.before = before
        self.after = after

    def __call__(self, bugsnag):

        def middleware(notification):
            if self.before:
                ret = self.before(notification)
                if ret is False:
                    return

            bugsnag(notification)

            if self.after:
                self.after(notification)

        return middleware

class DefaultMiddleware(object):
    """
    DefaultMiddleware provides the transformation from request_config into meta-data
    that has always been supported by bugsnag-python.
    """
    def __init__(self, bugsnag):
        self.bugsnag = bugsnag

    def __call__(self, notification):
        notification.set_user(id=notification.request_config.user_id)
        notification.set_user(**notification.request_config.user)
        notification.grouping_hash = notification.request_config.get("grouping_hash")

        if not notification.context:
            notification.context = notification.request_config.get("context")

        for name, dictionary in notification.request_config.meta_data.items():
            notification.add_tab(name, dictionary)

        notification.add_tab("request", notification.request_config.get("request_data"))
        notification.add_tab("environment", notification.request_config.get("environment_data"))
        notification.add_tab("session", notification.request_config.get("session_data"))
        notification.add_tab("extraData", notification.request_config.get("extra_data"))

        self.bugsnag(notification)

class MiddlewareStack(object):
    """
    Manages a stack of Bugsnag middleware.
    """
    def __init__(self):
        self.stack = []

    def before_notify(self, func):
        """
        Add a function to be run before bugsnag is notified.

        This lets you modify the payload that will be sent.
        If your function returns False, nothing will be sent.

        >>> def add_request_data(notification):
        ...    notification.add_tab("request", request_data)
        ...
        ... bugsnag.middleware.before_notify(add_request_data)
        """
        self.append(SimpleMiddleware(before=func))

    def after_notify(self, func):
        """
        Add a function to be run after bugsnag is notified.

        This lets you log errors in custom ways.
        """
        self.append(SimpleMiddleware(after=func))

    def append(self, middleware):
        """
        Add a middleware to the end of the stack.

        It will be run after all middleware currently defined.
        If you want to stop the notification progress, return from
        your __call__ method without calling the next level.

        >>> class ExampleMiddleware():
        ...     def __init__(self, bugsnag):
        ...         self.bugsnag = bugsnag
        ...
        ...     def __call__(self, notification):
        ...         notification.add_tab("request", notification.request_config.get("request")))
        ...         self.bugsnag(notification)
        ...
        >>> bugsnag.middleware.append(ExampleMiddleware)
        """
        self.stack.append(middleware)

    def run(self, notification, callback):
        """
        Run all the middleware in order, then call the callback.
        """

        # the last step in the notification stack is to call the callback.
        # we also do this inside the exception handler, so need to ensure that
        # the callback is only called once.
        def finish(notification):
            if not hasattr(finish, 'called'):
                finish.called = True
                callback()

        to_call = finish
        for middleware in reversed(self.stack):
            to_call = middleware(to_call)

        try:
            to_call(notification)
        except Exception as exc:
            bugsnag.log("Error in exception middleware: %s" % exc)
            # still notify if middleware crashes before notification
            finish(notification)
