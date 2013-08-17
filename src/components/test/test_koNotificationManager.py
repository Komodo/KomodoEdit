import itertools, time, unittest
from contextlib import contextmanager
from xpcom import components, COMException
from xpcom.server import UnwrapObject

Ci = components.interfaces
koINotificationManager = Ci.koINotificationManager

class NotificationManagerTestCase(unittest.TestCase):
    _com_interfaces_ = []

    @property
    def nm(self):
        """Short hand to get a notification manager"""
        if not hasattr(self, "_nm"):
            setattr(self, "_nm",
                    components.classes["@activestate.com/koNotification/manager;1"]\
                         .getService(koINotificationManager))
        return self._nm

    def _waitForCompletion(self):
        """Drain all pending events on the main thread"""
        thread = components.classes["@mozilla.org/thread-manager;1"]\
                           .getService(Ci.nsIThreadManager)\
                           .mainThread
        while thread.processNextEvent(False):
            pass

    def _wrap(self, aObject, aInterface=None):
        """Return the object with XPCOM wrappers"""
        sip = getattr(self, "__sip", None)
        if sip is None:
            sip = components.classes["@mozilla.org/supports-interface-pointer;1"]\
                            .createInstance(Ci.nsISupportsInterfacePointer)
            setattr(self, "__sip", sip)
        sip.data = aObject
        result = sip.data
        sip.data = None
        if aInterface is not None:
            result.QueryInterface(aInterface)
        return result

    def setUp(self):
        """Remove any existing notifications, in case some other part of the
        test suite has added anything.  Ignore any errors, so we actually show
        them in the test case."""
        try:
            for notification in self.nm.getAllNotifications():
                self.nm.removeNotification(notification)
        except:
            pass

    @contextmanager
    def check_called(self, notification, will_call=True, old_index=-1, new_index=-1,
                     reason=Ci.koINotificationListener.REASON_UPDATED):
        """Make sure that some operation will cause a listener to fire
        @param notification The notification the listener expects
        @param will_call Whether the listener should be called
        @param oldIndex The expected old index that will be passed to the listener
        @param newIndex The expected new index that will be passed to the listener
        @param reason The expected reason that will be passed to the listener
        """
        called = set() # used as a boolean, but in scope of the listener
        def listener(aNotification, aOldIndex, aNewIndex, aReason):
            self.assertEquals(aNotification, notification)
            self.assertEquals(aOldIndex, old_index)
            self.assertEquals(aNewIndex, new_index)
            self.assertEquals(aReason, reason)
            called.add(True)
        self.nm.addListener(listener)
        try:
            self.assertFalse(called,
                             "listener called right after adding it")
            yield
            self._waitForCompletion()
            if will_call:
                self.assertTrue(called,
                                "expected listener to be called but it wasn't")
            else:
                self.assertFalse(called,
                                 "listener called when it shouldn't be")
        except:
            # we usually get really useless stacks due to XPCOM + contextlib;
            # manually print out a stack of sorts so it can be debugged
            import inspect
            for frame in inspect.stack():
                print '  File "%s", line %r, in %s' % (frame[1], frame[2], frame[3])
            raise
        finally:
            self.nm.removeListener(listener)

    def test_01_getService(self):
        """Make sure we can get the notification manager"""
        self.assertNotEquals(self.nm, None)

    def test_02_empty(self):
        """Make sure the notification manager is initially empty"""
        self.assertEquals(self.nm.notificationCount, 0)
        self.assertEquals(self.nm.getAllNotifications(), [])

    def test_03_add(self):
        """Test adding, removing, and enumerating notifications"""
        # create two notifications, but don't add them
        notif = self.nm.createNotification("test-add-1", ["some", "tag"])
        notif2 = self.nm.createNotification("test-add-2", ["some", "tag"])
        self.assertNotEquals(notif, None)
        self.assertFalse(self.nm.hasNotification(notif))
        self.assertNotEquals(notif2, None)
        self.assertFalse(self.nm.hasNotification(notif2))
        self.assertEquals(self.nm.getAllNotifications(), [])
        self.assertEquals(self.nm.notificationCount, len(self.nm.getAllNotifications()))

        # add the first one
        self.nm.addNotification(notif)
        self.assertEquals(self.nm.getAllNotifications(), [notif])
        self.assertTrue(self.nm.hasNotification(notif))
        self.assertFalse(self.nm.hasNotification(notif2))
        self.assertEquals(self.nm.notificationCount, len(self.nm.getAllNotifications()))

        # add the first one again (no change)
        self.nm.addNotification(notif)
        self.assertEquals(self.nm.getAllNotifications(), [notif])
        self.assertTrue(self.nm.hasNotification(notif))
        self.assertFalse(self.nm.hasNotification(notif2))
        self.assertEquals(self.nm.notificationCount, len(self.nm.getAllNotifications()))

        # add the second one
        self.nm.addNotification(notif2)
        self.assertEquals(self.nm.getAllNotifications(), [notif, notif2])
        self.assertTrue(self.nm.hasNotification(notif))
        self.assertTrue(self.nm.hasNotification(notif2))
        self.assertEquals(self.nm.notificationCount, len(self.nm.getAllNotifications()))

        # remove the first one
        self.assertTrue(self.nm.removeNotification(notif))
        self.assertFalse(self.nm.hasNotification(notif))
        self.assertTrue(self.nm.hasNotification(notif2))
        self.assertEquals(self.nm.getAllNotifications(), [notif2])
        self.assertEquals(self.nm.notificationCount, len(self.nm.getAllNotifications()))

        # remove the second one, now empty
        self.assertTrue(self.nm.removeNotification(notif2))
        self.assertFalse(self.nm.hasNotification(notif))
        self.assertFalse(self.nm.hasNotification(notif2))
        self.assertEquals(self.nm.getAllNotifications(), [])
        self.assertEquals(self.nm.notificationCount, len(self.nm.getAllNotifications()))

        # remove notifications that aren't there
        self.assertFalse(self.nm.removeNotification(notif))
        self.assertFalse(self.nm.removeNotification(None))

    def test_04_add_repeat(self):
        """Check that creating a new notification with the same identifier/context
        returns the previous notification"""
        self.assertEquals(self.nm.getAllNotifications(), [])
        try:
            notif1 = self.nm.createNotification("test-notif-repeat", ["some", "tag"])
            with self.check_called(notif1, reason=Ci.koINotificationListener.REASON_ADDED, new_index=0):
                self.nm.addNotification(notif1)
            notif2 = self.nm.createNotification("test-notif-repeat", ["some", "tag"])
            self.assertEquals(notif1, notif2) # same identifier + context
            notif3 = self.nm.createNotification("test-notif-repeat", ["some", "tag"],
                                                str(time.time()))
            self.assertNotEquals(notif1, notif3) # different context
        finally:
            self.nm.removeNotification(notif1)
            self.assertEquals(self.nm.getAllNotifications(), [])
 
    def test_05_notification_interfaces(self):
        """Check that creating notifications returns instances with the expected
        interfaces exposed"""
        iface_map = {
            koINotificationManager.TYPE_ACTIONABLE:
                Ci.koINotificationActionable,
            koINotificationManager.TYPE_PROGRESS:
                Ci.koINotificationProgress,
            koINotificationManager.TYPE_TEXT:
                Ci.koINotificationText,
        }
        for flags in range(8):
            n = self.nm.createNotification("", [], None, flags)
            self.assertEquals(n.QueryInterface(Ci.koINotification), n)
            for flag in iface_map.keys():
                if flags & flag:
                    self.assertEquals(n.QueryInterface(iface_map[flag]), n)
                else:
                    self.assertRaises(COMException,
                                      n.QueryInterface, iface_map[flag])

    def test_06_notification_listeners(self):
        """Check that listeners are fired when notifications are added or
        removed"""
        notif = self.nm.createNotification("test-listen-one", [])
        notif2 = self.nm.createNotification("test-listen-two", [])
        REASON_ADDED   = Ci.koINotificationListener.REASON_ADDED
        REASON_UPDATED = Ci.koINotificationListener.REASON_UPDATED
        REASON_REMOVED = Ci.koINotificationListener.REASON_REMOVED

        def do_check(operation, expected_old_index, expected_new_index,
                     expected_reason, notif=None):
            with self.check_called(notif, will_call=(expected_reason is not None),
                                   old_index=expected_old_index,
                                   new_index=expected_new_index,
                                   reason=expected_reason):
                operation(notif)

        do_check(self.nm.addNotification,    -1,  0, REASON_ADDED,   notif)
        do_check(self.nm.addNotification,     0,  0, REASON_UPDATED, notif)
        do_check(self.nm.addNotification,    -1,  1, REASON_ADDED,   notif2)
        do_check(self.nm.removeNotification,  0, -1, REASON_REMOVED, notif)
        do_check(self.nm.removeNotification,  0, -1, None,           notif)
        do_check(self.nm.addNotification,    -1,  1, REASON_ADDED,   notif)
        do_check(self.nm.addNotification,     0,  1, REASON_UPDATED, notif2)
        do_check(self.nm.removeNotification,  0, -1, REASON_REMOVED, notif)
        do_check(self.nm.removeNotification,  0, -1, REASON_REMOVED, notif2)

    def test_07_notification_basic(self):
        """Check that the basic notification interface (koINotification) works"""
        self.assertEquals(self.nm.notificationCount, 0)
        notif = self.nm.createNotification("notif-basic", ["tags"])
        self.assertEquals(0, notif.time) # not fired
        self.nm.addNotification(notif)
        try:
            self.assertAlmostEquals(time.time(), float(notif.time) / 10**6, 0)
            self.assertEquals(notif.getTags(), ["tags"])
            self.assertEquals(notif.identifier, "notif-basic")
            for attr in ("summary", "iconURL", "description"):
                with self.check_called(notif, will_call=False):
                    setattr(notif, attr, attr * 2)
                with self.check_called(notif, will_call=False):
                    setattr(notif, attr, attr * 2)
                    self.assertEquals(getattr(notif, attr), attr * 2)
            with self.check_called(notif, will_call=False):
                notif.severity = 1
            self.assertEquals(notif.severity, 1)

            context = str(time.time())
            notif2 = self.nm.createNotification("notif-basic", [], context)
            self.assertNotEquals(notif, notif2) # different context
            self.assertEquals(notif2.contxt, context)
            with self.check_called(notif2, new_index=1,
                                   reason=Ci.koINotificationListener.REASON_ADDED):
                self.nm.addNotification(notif2)

            notif3 = self.nm.createNotification("notif-basic", [], context)
            self.assertEquals(notif2, notif3) # same context
            
            self.assertEquals(self.nm.getAllNotifications(), [notif, notif2])
        finally:
            for notif in self.nm.getAllNotifications():
                self.nm.removeNotification(notif)
            self.assertEquals(self.nm.notificationCount, 0)

    # No longer run, as notifications no longer notify listeners when they have
    # been modified.
    #def test_08_notification_progress(self):
    #    """Check koINotificationProgress"""
    #    self.assertEquals(self.nm.notificationCount, 0)
    #    notif = self.nm.createNotification("notif-progress", ["tags"], None,
    #                                       koINotificationManager.TYPE_PROGRESS)
    #    notif.QueryInterface(Ci.koINotificationProgress)
    #    self.nm.addNotification(notif)
    #
    #    try:
    #        self.assertRaises(COMException,
    #                          setattr, notif, "maxProgress", -2)
    #        self.assertTrue(hasattr(Ci.koINotificationProgress,
    #                                "PROGRESS_INDETERMINATE"))
    #        with self.check_called(notif, True, old_index=0, new_index=0):
    #            notif.maxProgress = 5
    #        self.assertAlmostEquals(notif.maxProgress, 5)
    #        with self.check_called(notif, False):
    #            notif.progress = 0
    #        self.assertAlmostEquals(notif.progress, 0)
    #        with self.check_called(notif, True, old_index=0, new_index=0):
    #            notif.progress = 5
    #        self.assertAlmostEquals(notif.progress, 5)
    #        with self.check_called(notif, False):
    #            notif.progress = 5
    #        self.assertRaises(COMException,
    #                          setattr, notif, "progress", 10) # > maxProgress
    #        self.assertAlmostEquals(notif.progress, 5)
    #        with self.check_called(notif, True, old_index=0, new_index=0):
    #            notif.maxProgress = 10
    #        self.assertAlmostEquals(notif.maxProgress, 10)
    #        with self.check_called(notif, True, old_index=0, new_index=0):
    #            notif.progress = 10
    #        self.assertAlmostEquals(notif.progress, 10)
    #    finally:
    #        self.nm.removeNotification(notif)
    #        self.assertEquals(self.nm.notificationCount, 0)

    def test_09_notification_actionable(self):
        """Check koINotificationActionable"""
        def Action(identifier=None):
            action = components.classes["@activestate.com/koNotification/action;1"]\
                               .createInstance()
            if identifier:
                action.identifier = identifier
            return action

        self.assertEquals(self.nm.notificationCount, 0)
        notif = self.nm.createNotification("notif-action", ["more", "tags"], None,
                                           koINotificationManager.TYPE_ACTIONABLE)
        notif.QueryInterface(Ci.koINotificationActionable)
        self.nm.addNotification(notif)

        try:
            self.assertEquals(notif.getActions(), [])
            action0 = Action()

            # check that we can't insert an uninitialized action
            self.assertRaises(COMException,
                              notif.updateAction, action0)
            action0.identifier = "action 0"
            # can't re-initialize an action
            self.assertRaises(COMException,
                              setattr, action0, "identifier", "dummy")

            # add an action normally
            with self.check_called(notif, old_index=0, new_index=0):
                notif.updateAction(action0)
            self.assertEquals(notif.getActions(), [action0])
            # re-insert (i.e. update) an action
            with self.check_called(notif, old_index=0, new_index=0):
                notif.updateAction(action0)
            self.assertEquals(notif.getActions(), [action0])

            action1 = Action("action 1")
            # append an action
            with self.check_called(notif, old_index=0, new_index=0):
                notif.updateAction(action1)
            self.assertEquals(notif.getActions(), [action0, action1])
            # update the action
            with self.check_called(notif, old_index=0, new_index=0):
                notif.updateAction(action1)
            self.assertEquals(notif.getActions(), [action0, action1])
            # make sure updating the first action doesn't change order
            with self.check_called(notif, old_index=0, new_index=0):
                notif.updateAction(action0)
            self.assertEquals(notif.getActions(), [action0, action1])

        finally:
            self.nm.removeNotification(notif)
            self.assertEquals(self.nm.notificationCount, 0)

    def test_10_get_filtered(self):
        """Test getting notifications by contexts and identifiers"""
        self.assertEquals(self.nm.notificationCount, 0)
        all_contexts = [None] + map(str, range(1, 6))
        all_notifications = []
        try:
            for i in range(10 * len(all_contexts)):
                notification = self.nm.createNotification(str(i), [], all_contexts[i % len(all_contexts)])
                self.nm.addNotification(notification)
                all_notifications.append(notification)

            def testContexts(contexts):
                notifications = self.nm.getNotifications(contexts)
                for notification in notifications:
                    self.assertTrue(notification.contxt in contexts)
                    context = contexts[contexts.index(notification.contxt)]
                    if context is None:
                        self.assertEquals(int(notification.identifier) % len(all_contexts), 0)
                    else:
                        self.assertEquals(int(notification.identifier) % len(all_contexts), int(context))
                self.assertEquals(len(notifications), 10 * len(contexts))

            for length in range(1, len(all_contexts) + 1):
                for contexts in itertools.combinations(all_contexts, length):
                    testContexts(contexts)

            # passing in no contexts gets everything regardless of context
            notifications = self.nm.getNotifications([])
            for notification in notifications:
                self.assertTrue(notification in all_notifications)
            self.assertEquals(len(notifications), len(all_notifications))

            for i in range(len(all_notifications)):
                # getting by identifier should return the desired notification
                self.assertEquals([all_notifications[i]],
                                  self.nm.getNotifications([], str(i)))
                # get by identifier, with matching context
                context = all_contexts[i % len(all_contexts)]
                self.assertEquals([all_notifications[i]],
                                  self.nm.getNotifications([context], str(i)))
                # get by identifier, with mismatched context
                context = all_contexts[(i + 1) % len(all_contexts)]
                self.assertEquals([],
                                  self.nm.getNotifications([context], str(i)))

        finally:
            for notification in all_notifications:
                self.nm.removeNotification(notification)
            self.assertEquals(self.nm.notificationCount, 0)

    def test_11_python_interface(self):
        """Test the more Python API"""
        self.assertEquals(self.nm.notificationCount, 0)
        nm = UnwrapObject(self.nm)
        kwargs = { "iconURL": "icon URL",
                   "severity": Ci.koINotification.SEVERITY_WARNING,
                   "description": "description",
                   "details": "details",
                   "maxProgress": 10,
                   "progress": 5 }
        notif = nm.add("summary", ["tags"], "notif-ident", **kwargs)
        try:
            self.assertEquals(notif, self._wrap(notif)) # should already be wrapped
            notif.QueryInterface(Ci.koINotification) # should implement this
            notif.QueryInterface(Ci.koINotificationProgress) # due to maxProgress
            notif.QueryInterface(Ci.koINotificationText) # due to details
            self.assertEquals(notif.summary, "summary")
            self.assertEquals(notif.getTags(), ["tags"])
            self.assertEquals(notif.identifier, "notif-ident")
            self.assertEquals(self.nm.notificationCount, 1) # added one notification

            notif2 = nm.add("modified-summary", [], "notif-ident")
            self.assertEquals(notif, notif2) # no context, same identifier
            self.assertEquals(notif.summary, "modified-summary") # got the new one
            self.assertEquals(notif.getTags(), ["tags"]) # kept the old one

            for k, v in kwargs.items():
                self.assertEquals(getattr(notif, k), v)
            updates = { "summary": "new summary",
                        "details": "new details",
                        "progress": 2 }
            nm.update(notif, **updates)
            for k, v in updates.items():
                self.assertEquals(getattr(notif, k), v)
            self.assertRaises(COMException,
                              nm.update, notif, progress=20)

            # check listeners get hooked up correctly
            # No longer tested as notification changes do not notify listeners.
            #called = set()
            #def listener(aNotification, aOldIndex, aNewIndex, aReason):
            #    self.assertEquals(aNotification, notif)
            #    self.assertEquals(aOldIndex, 0)
            #    self.assertEquals(aNewIndex, 0)
            #    self.assertEquals(aReason, Ci.koINotificationListener.REASON_UPDATED)
            #    called.add(True)
            #nm.addListener(listener)
            #notif.progress = 9
            #self._waitForCompletion()
            #self.assertTrue(called, "expected listener to be called due to progress change")
            #nm.removeListener(listener)
            #called.discard(True)
            #notif.progress = 10
            #self._waitForCompletion()
            #self.assertFalse(called, "did not expect listener to be called because it was removed")

            # test python iterable
            self.assertEquals(len(nm), 1)
            self.assertEquals(nm[0], notif)
            self.assertEquals([x for x in nm], [notif])
            self.assertTrue(notif in nm)
            self.assertEquals(nm.count(notif), 1)
            self.assertEquals(nm.index(notif), 0)

        finally:
            nm.remove(notif)
            self.assertEquals(self.nm.notificationCount, 0)

    def test_12_python_actions(self):
        """Test Python API with actions"""
        self.assertEquals(self.nm.notificationCount, 0)
        nm = UnwrapObject(self.nm)
        a0_data = { "identifier": "action0",
                    "label": "action0-label",
                    "accessKey": "a",
                    "iconURL": "action-url",
                    "visible": True,
                    "enabled": True }
        notif = nm.add("summary", ["tags"], "notif-action-py", actions=[a0_data])
        self.assertEquals(notif, self._wrap(notif)) # should already be wrapped
        notif.QueryInterface(Ci.koINotification) # should implement this
        notif.QueryInterface(Ci.koINotificationActionable) # due to actions=
        self.assertEquals(self.nm.notificationCount, 1) # added one notification
        try:
            self.assertEquals(len(notif.getActions()), 1)
            self.assertEquals(len(notif.getActions("bad-id")), 0)
            self.assertEquals(len(notif.getActions("action0")), 1)
            action = notif.getActions()[0]
            self.assertEquals(action, self._wrap(action))
            for k, v in a0_data.items():
                self.assertEquals(getattr(action, k), v)
            for k in ("label", "accessKey", "iconURL"):
                with self.check_called(notif, will_call=False):
                    # changing the action won't force an update
                    self.assertNotEquals(getattr(action, k), k)
                    setattr(action, k, k)
                    self.assertEquals(getattr(action, k), k)
            with self.check_called(notif, old_index=0, new_index=0):
                # calling the right update API, however, will fire listeners
                nm.update(notif, actions=[{ "identifier": "action0",
                                            "label": "new label"}])
                self.assertEquals(action.label, "new label")
            self.assertRaises(COMException,
                              nm.update, notif, actions=[{"label": "foo"}])
            self.assertRaises(COMException,
                              nm.update, notif, actions=[{"identifier": "action0",
                                                          "invalid": "key"}])

        finally:
            nm.remove(notif)
            self.assertEquals(self.nm.notificationCount, 0)
