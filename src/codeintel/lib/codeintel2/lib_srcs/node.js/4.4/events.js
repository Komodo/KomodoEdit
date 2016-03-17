/**
 * Much of the Node.js core API is built around an idiomatic asynchronous
 * event-driven architecture in which certain kinds of objects (called
 * "emitters") periodically emit named events that cause Function objects
 * ("listeners") to be called.
 */
var events = {};

/**
 * The EventEmitter class is defined and exposed by the events module:
 * @constructor
 */
events.EventEmitter = function() {}

/**
 * Alias for emitter.on(event, listener).
 * @param event
 * @param listener
 */
events.EventEmitter.prototype.addListener = function(event, listener) {}

/**
 * Removes all listeners, or those of the specified event.
 * @param event
 */
events.EventEmitter.prototype.removeAllListeners = function(event) {}

/**
 * By default EventEmitters will print a warning if more than 10 listeners
 * are added for a particular event. This is a useful default that helps
 * finding memory leaks. Obviously, not all events should be limited to
 * just 10 listeners.
 * @param n
 */
events.EventEmitter.prototype.setMaxListeners = function(n) {}

/**
 * Returns a copy of the array of listeners for the specified event.
 * @param event
 * @returns a copy of the array of listeners for the specified event
 */
events.EventEmitter.prototype.listeners = function(event) {}

/**
 * Synchronously calls each of the listeners registered for event, in the
 * order they were registered, passing the supplied arguments to each.
 * @param event
 * @param arg1
 * @param arg2
 */
events.EventEmitter.prototype.emit = function(event, arg1, arg2) {}

/**
 * Removes the specified listener from the listener array for the specified
 * event.
 * @param event
 * @param listener
 */
events.EventEmitter.prototype.removeListener = function(event, listener) {}

/**
 * Adds a one time listener function for the event. This listener is
 * invoked only the next time event is triggered, after which it is
 * removed.
 * @param event
 * @param listener
 */
events.EventEmitter.prototype.once = function(event, listener) {}

/**
 * By default, a maximum of 10 listeners can be registered for any single
 * event. This limit can be changed for individual EventEmitter instances
 * using the [emitter.setMaxListeners(n)][] method. To change the default
 * for all EventEmitter instances, the EventEmitter.defaultMaxListeners
 * property can be used.
 */
events.EventEmitter.prototype.defaultMaxListeners = 0;

/**
 * Returns the current max listener value for the EventEmitter which is
 * either set by [emitter.setMaxListeners(n)][] or defaults to
 * [EventEmitter.defaultMaxListeners][].
 * @returns the current max listener value for the EventEmitter which is either set by emitter.setMaxListeners(n) or defaults to EventEmitter.defaultMaxListeners
 */
events.EventEmitter.prototype.getMaxListeners = function() {}

/**
 * A class method that returns the number of listeners for the given event
 * registered on the given emitter.
 * @param emitter
 * @param event
 */
events.EventEmitter.prototype.listenerCount = function(emitter, event) {}

/**
 * Returns the number of listeners listening to the event type.
 * @param event {Value}
 * @returns {Number} the number of listeners listening to the event type
 */
events.EventEmitter.prototype.listenerCount = function(event) {}

/**
 * Adds the listener function to the end of the listeners array for the
 * specified event. No checks are made to see if the listener has already
 * been added. Multiple calls passing the same combination of event and
 * listener will result in the listener being added, and called, multiple
 * times.
 * @param event
 * @param listener
 */
events.EventEmitter.prototype.on = function(event, listener) {}

/** @__local__ */ events.EventEmitter.__events__ = {};

/**
 * The EventEmitter instance will emit it&#39;s own &#39;newListener&#39;
 * event before a listener is added to it&#39;s internal array of
 * listeners. Listeners registered for the &#39;newListener&#39; event will
 * be passed the event name and a reference to the listener being added.
 * The fact that the event is triggered before adding the listener has a
 * subtle but important side effect: any additional listeners registered to
 * the same name within the &#39;newListener&#39; callback will be inserted
 * before the listener that is in the process of being added.
 * @param event {String}
 * @param listener {Function}
 */
events.EventEmitter.__events__.newListener = function(event, listener) {};

/**
 * The &#39;removeListener&#39; event is emitted after a listener is
 * removed.
 */
events.EventEmitter.__events__.removeListener = function() {};

exports = events;

