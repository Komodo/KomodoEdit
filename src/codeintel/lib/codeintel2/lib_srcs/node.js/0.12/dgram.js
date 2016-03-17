/**
 * Datagram sockets are available through require(&#39;dgram&#39;).
 */
var dgram = {};

/**
 * Creates a datagram Socket of the specified types. Valid types are udp4
 * and udp6.
 * @param type
 * @param callback
 * @returns {dgram.Socket}
 */
dgram.createSocket = function(type, callback) {}

/**
 * The options object should contain a type field of either udp4 or udp6
 * and an optional boolean reuseAddr field.
 * @param options
 * @param callback
 * @returns {dgram.Socket}
 */
dgram.createSocket = function(options, callback) {}

/**
 * The dgram Socket class encapsulates the datagram functionality. It
 * should be created via dgram.createSocket(...)
 * @constructor
 */
dgram.Socket = function() {}
dgram.Socket.prototype = new events.EventEmitter();

/**
 * Tells the kernel to join a multicast group with IP_ADD_MEMBERSHIP socket
 * option.
 * @param multicastAddress {String}
 * @param multicastInterface {String}
 */
dgram.Socket.prototype.addMembership = function(multicastAddress, multicastInterface) {}

/**
 * For UDP sockets, listen for datagrams on a named port and optional
 * address. If address is not specified, the OS will try to listen on all
 * addresses. After binding is done, a "listening" event is emitted and the
 * callback(if specified) is called. Specifying both a "listening" event
 * listener and callback is not harmful but not very useful.
 * @param port
 * @param address {String}
 * @param callback
 */
dgram.Socket.prototype.bind = function(port, address, callback) {}

/**
 * The port and address properties of options, as well as the optional
 * callback function, behave as they do on a call to socket.bind(port,
 * [address], [callback]) .
 * @param options {Object}
 * @param callback {Function}
 */
dgram.Socket.prototype.bind = function(options, callback) {}

/**
 * Sets the IP_MULTICAST_TTL socket option. TTL stands for "Time to Live,"
 * but in this context it specifies the number of IP hops that a packet is
 * allowed to go through, specifically for multicast traffic. Each router
 * or gateway that forwards a packet decrements the TTL. If the TTL is
 * decremented to 0 by a router, it will not be forwarded.
 * @param ttl
 */
dgram.Socket.prototype.setMulticastTTL = function(ttl) {}

/**
 * For UDP sockets, the destination port and address must be specified. A
 * string may be supplied for the address parameter, and it will be
 * resolved with DNS.
 * @param buf
 * @param offset
 * @param length
 * @param port
 * @param address
 * @param callback
 */
dgram.Socket.prototype.send = function(buf, offset, length, port, address, callback) {}

/**
 * Sets or clears the IP_MULTICAST_LOOP socket option. When this option is
 * set, multicast packets will also be received on the local interface.
 * @param flag
 */
dgram.Socket.prototype.setMulticastLoopback = function(flag) {}

/**
 * Sets the IP_TTL socket option. TTL stands for "Time to Live," but in
 * this context it specifies the number of IP hops that a packet is allowed
 * to go through. Each router or gateway that forwards a packet decrements
 * the TTL. If the TTL is decremented to 0 by a router, it will not be
 * forwarded. Changing TTL values is typically done for network probes or
 * when multicasting.
 * @param ttl
 */
dgram.Socket.prototype.setTTL = function(ttl) {}

/**
 * Sets or clears the SO_BROADCAST socket option. When this option is set,
 * UDP packets may be sent to a local interface&#39;s broadcast address.
 * @param flag
 */
dgram.Socket.prototype.setBroadcast = function(flag) {}

/**
 * Returns an object containing the address information for a socket. For
 * UDP sockets, this object will contain address , family and port.
 * @returns an object containing the address information for a socket
 */
dgram.Socket.prototype.address = function() {}

/**
 * Close the underlying socket and stop listening for data on it.
 */
dgram.Socket.prototype.close = function() {}

/**
 * Opposite of addMembership - tells the kernel to leave a multicast group
 * with IP_DROP_MEMBERSHIP socket option. This is automatically called by
 * the kernel when the socket is closed or process terminates, so most apps
 * will never need to call this.
 * @param multicastAddress {String}
 * @param multicastInterface {String}
 */
dgram.Socket.prototype.dropMembership = function(multicastAddress, multicastInterface) {}

/**
 * Opposite of unref, calling ref on a previously unrefd socket will not
 * let the program exit if it&#39;s the only socket left (the default
 * behavior). If the socket is refd calling ref again will have no effect.
 */
dgram.Socket.prototype.ref = function() {}

/**
 * Calling unref on a socket will allow the program to exit if this is the
 * only active socket in the event system. If the socket is already unrefd
 * calling unref again will have no effect.
 */
dgram.Socket.prototype.unref = function() {}

/** @__local__ */ dgram.Socket.__events__ = {};

/**
 * Emitted when a new datagram is available on a socket. msg is a Buffer
 * and rinfo is an object with the sender&#39;s address information:
 * @param msg {buffer.Buffer}
 * @param rinfo {Object}
 */
dgram.Socket.__events__.message = function(msg, rinfo) {};

/**
 * Emitted when a socket starts listening for datagrams. This happens as
 * soon as UDP sockets are created.
 */
dgram.Socket.__events__.listening = function() {};

/**
 * Emitted when a socket is closed with close(). No new message events will
 * be emitted on this socket.
 */
dgram.Socket.__events__.close = function() {};

/**
 * Emitted when an error occurs.
 * @param exception {Error}
 */
dgram.Socket.__events__.error = function(exception) {};

var events = require("events");

exports = dgram;

