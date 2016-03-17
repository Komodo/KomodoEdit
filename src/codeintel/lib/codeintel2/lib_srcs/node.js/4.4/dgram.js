/**
 * The dgram module provides an implementation of UDP Datagram sockets.
 */
var dgram = {};

/**
 * The dgram.Socket object is an [EventEmitter][] that encapsulates the
 * datagram functionality.
 * @constructor
 */
dgram.Socket = function() {}
dgram.Socket.prototype = new events.EventEmitter();

/**
 * Tells the kernel to join a multicast group at the given multicastAddress
 * using the IP_ADD_MEMBERSHIP socket option. If the multicastInterface
 * argument is not specified, the operating system will try to add
 * membership to all valid networking interfaces.
 * @param multicastAddress {String}
 * @param multicastInterface {String}
 */
dgram.Socket.prototype.addMembership = function(multicastAddress, multicastInterface) {}

/**
 * For UDP sockets, causes the dgram.Socket to listen for datagram messages
 * on a named port and optional address. If port is not specified, the
 * operating system will attempt to bind to a random port. If address is
 * not specified, the operating system will attempt to listen on all
 * addresses. Once binding is complete, a &#39;listening&#39; event is
 * emitted and the optional callback function is called.
 * @param port {Number}
 * @param address {String}
 * @param callback {Function}
 */
dgram.Socket.prototype.bind = function(port, address, callback) {}

/**
 * For UDP sockets, causes the dgram.Socket to listen for datagram messages
 * on a named port and optional address that are passed as properties of an
 * options object passed as the first argument. If port is not specified,
 * the operating system will attempt to bind to a random port. If address
 * is not specified, the operating system will attempt to listen on all
 * addresses. Once binding is complete, a &#39;listening&#39; event is
 * emitted and the optional callback function is called.
 * @param options {Object}
 * @param callback {Function}
 */
dgram.Socket.prototype.bind = function(options, callback) {}

/**
 * Sets the IP_MULTICAST_TTL socket option. While TTL generally stands for
 * "Time to Live", in this context it specifies the number of IP hops that
 * a packet is allowed to travel through, specifically for multicast
 * traffic. Each router or gateway that forwards a packet decrements the
 * TTL. If the TTL is decremented to 0 by a router, it will not be
 * forwarded.
 * @param ttl {Number}
 */
dgram.Socket.prototype.setMulticastTTL = function(ttl) {}

/**
 * Broadcasts a datagram on the socket. The destination port and address
 * must be specified.
 * @param buf {Buffer|String}
 * @param offset {Number}
 * @param length {Number}
 * @param port {Number}
 * @param address {String}
 * @param callback {Function}
 */
dgram.Socket.prototype.send = function(buf, offset, length, port, address, callback) {}

/**
 * Sets or clears the IP_MULTICAST_LOOP socket option. When set to true,
 * multicast packets will also be received on the local interface.
 * @param flag {Boolean}
 */
dgram.Socket.prototype.setMulticastLoopback = function(flag) {}

/**
 * Sets the IP_TTL socket option. While TTL generally stands for "Time to
 * Live", in this context it specifies the number of IP hops that a packet
 * is allowed to travel through. Each router or gateway that forwards a
 * packet decrements the TTL. If the TTL is decremented to 0 by a router,
 * it will not be forwarded.
 * @param ttl {Number}
 */
dgram.Socket.prototype.setTTL = function(ttl) {}

/**
 * Sets or clears the SO_BROADCAST socket option. When set to true, UDP
 * packets may be sent to a local interface&#39;s broadcast address.
 * @param flag {Boolean}
 */
dgram.Socket.prototype.setBroadcast = function(flag) {}

/**
 * Returns an object containing the address information for a socket.
 * @returns an object containing the address information for a socket
 */
dgram.Socket.prototype.address = function() {}

/**
 * Close the underlying socket and stop listening for data on it. If a
 * callback is provided, it is added as a listener for the
 * [&#39;close&#39;][] event.
 * @param callback
 */
dgram.Socket.prototype.close = function(callback) {}

/**
 * Instructs the kernel to leave a multicast group at multicastAddress
 * using the IP_DROP_MEMBERSHIP socket option. This method is automatically
 * called by the kernel when the socket is closed or the process
 * terminates, so most apps will never have reason to call this.
 * @param multicastAddress {String}
 * @param multicastInterface {String}
 */
dgram.Socket.prototype.dropMembership = function(multicastAddress, multicastInterface) {}

/**
 * By default, binding a socket will cause it to block the Node.js process
 * from exiting as long as the socket is open. The socket.unref() method
 * can be used to exclude the socket from the reference counting that keeps
 * the Node.js process active. The socket.ref() method adds the socket back
 * to the reference counting and restores the default behavior.
 */
dgram.Socket.prototype.ref = function() {}

/**
 * By default, binding a socket will cause it to block the Node.js process
 * from exiting as long as the socket is open. The socket.unref() method
 * can be used to exclude the socket from the reference counting that keeps
 * the Node.js process active, allowing the process to exit even if the
 * socket is still listening.
 */
dgram.Socket.prototype.unref = function() {}

/** @__local__ */ dgram.Socket.__events__ = {};

/**
 * The &#39;close&#39; event is emitted after a socket is closed with
 * [close()][]. Once triggered, no new &#39;message&#39; events will be
 * emitted on this socket.
 */
dgram.Socket.__events__.close = function() {};

/**
 * The &#39;error&#39; event is emitted whenever any error occurs. The
 * event handler function is passed a single Error object.
 * @param exception {Error}
 */
dgram.Socket.__events__.error = function(exception) {};

/**
 * The &#39;listening&#39; event is emitted whenever a socket begins
 * listening for datagram messages. This occurs as soon as UDP sockets are
 * created.
 */
dgram.Socket.__events__.listening = function() {};

/**
 * The &#39;message&#39; event is emitted when a new datagram is available
 * on a socket. The event handler function is passed two arguments: msg and
 * rinfo. The msg argument is a [Buffer][] and rinfo is an object with the
 * sender&#39;s address information provided by the address, family and
 * port properties:
 * @param msg {buffer.Buffer}
 * @param rinfo {Object}
 */
dgram.Socket.__events__.message = function(msg, rinfo) {};

var events = require("events");

exports = dgram;

