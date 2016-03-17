/**
 * The dns module contains functions belonging to two different categories:
 */
var dns = {};

/**
 * Uses the DNS protocol to resolve a hostname (e.g. &#39;nodejs.org&#39;)
 * into an array of the record types specified by rrtype.
 * @param hostname
 * @param rrtype
 * @param callback
 */
dns.resolve = function(hostname, rrtype, callback) {}

/**
 * Performs a reverse DNS query that resolves an IPv4 or IPv6 address to an
 * array of hostnames.
 * @param ip
 * @param callback
 */
dns.reverse = function(ip, callback) {}

/**
 * Uses the DNS protocol to resolve mail exchange records (MX records) for
 * the hostname. The addresses argument passed to the callback function
 * will contain an array of objects containing both a priority and exchange
 * property (e.g. [{priority: 10, exchange: &#39;mx.example.com&#39;},
 * ...]).
 * @param hostname
 * @param callback
 */
dns.resolveMx = function(hostname, callback) {}

/**
 * Uses the DNS protocol to resolve text queries (TXT records) for the
 * hostname. The addresses argument passed to the callback function is is a
 * two-dimentional array of the text records available for hostname (e.g.,
 * [ [&#39;v=spf1 ip4:0.0.0.0 &#39;, &#39;~all&#39; ] ]). Each sub-array
 * contains TXT chunks of one record. Depending on the use case, these
 * could be either joined together or treated separately.
 * @param hostname
 * @param callback
 */
dns.resolveTxt = function(hostname, callback) {}

/**
 * Uses the DNS protocol to resolve a IPv4 addresses (A records) for the
 * hostname. The addresses argument passed to the callback function will
 * contain an array of IPv4 addresses (e.g.
 * @param hostname
 * @param callback
 */
dns.resolve4 = function(hostname, callback) {}

/**
 * Uses the DNS protocol to resolve service records (SRV records) for the
 * hostname. The addresses argument passed to the callback function will be
 * an array of objects with the following properties:
 * @param hostname
 * @param callback
 */
dns.resolveSrv = function(hostname, callback) {}

/**
 * Uses the DNS protocol to resolve a IPv6 addresses (AAAA records) for the
 * hostname. The addresses argument passed to the callback function will
 * contain an array of IPv6 addresses.
 * @param hostname
 * @param callback
 */
dns.resolve6 = function(hostname, callback) {}

/**
 * Resolves a hostname (e.g. &#39;nodejs.org&#39;) into the first found A
 * (IPv4) or AAAA (IPv6) record. options can be an object or integer. If
 * options is not provided, then IPv4 and IPv6 addresses are both valid. If
 * options is an integer, then it must be 4 or 6.
 * @param hostname
 * @param options
 * @param callback
 */
dns.lookup = function(hostname, options, callback) {}

/**
 * Uses the DNS protocol to resolve CNAME records for the hostname. The
 * addresses argument passed to the callback function will contain an array
 * of canonical name records available for the hostname (e.g.
 * [&#39;bar.example.com&#39;]).
 * @param hostname
 * @param callback
 */
dns.resolveCname = function(hostname, callback) {}

/**
 * Uses the DNS protocol to resolve name server records (NS records) for
 * the hostname. The addresses argument passed to the callback function
 * will contain an array of name server records available for hostname
 * (e.g., [&#39;ns1.example.com&#39;, &#39;ns2.example.com&#39;]).
 * @param hostname
 * @param callback
 */
dns.resolveNs = function(hostname, callback) {}

/**
 * Returns an array of IP address strings that are being used for name
 * resolution.
 * @returns {Array} an array of IP address strings that are being used for name resolution
 */
dns.getServers = function() {}

/**
 * Resolves the given address and port into a hostname and service using
 * the operating system&#39;s underlying getnameinfo implementation.
 * @param address
 * @param port
 * @param callback
 */
dns.lookupService = function(address, port, callback) {}

/**
 * Uses the DNS protocol to resolve a start of authority record (SOA
 * record) for the hostname. The addresses argument passed to the callback
 * function will be an object with the following properties:
 * @param hostname
 * @param callback
 */
dns.resolveSoa = function(hostname, callback) {}

/**
 * Sets the IP addresses of the servers to be used when resolving. The
 * servers argument is an array of IPv4 or IPv6 addresses.
 * @param servers
 */
dns.setServers = function(servers) {}

exports = dns;

