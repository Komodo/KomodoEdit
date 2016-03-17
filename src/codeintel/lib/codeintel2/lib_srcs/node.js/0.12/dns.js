/**
 * Use require(&#39;dns&#39;) to access this module.
 */
var dns = {};

/**
 * Resolves a hostname (e.g. &#39;google.com&#39;) into the first found A
 * (IPv4) or AAAA (IPv6) record. options can be an object or integer. If
 * options is not provided, then IP v4 and v6 addresses are both valid. If
 * options is an integer, then it must be 4 or 6.
 * @param hostname
 * @param options
 * @param callback
 */
dns.lookup = function(hostname, options, callback) {}

/**
 * Resolves the given address and port into a hostname and service using
 * getnameinfo.
 * @param address
 * @param port
 * @param callback
 */
lookupService = function(address, port, callback) {}

/**
 * Resolves a hostname (e.g. &#39;google.com&#39;) into an array of the
 * record types specified by rrtype.
 * @param hostname
 * @param rrtype
 * @param callback
 */
lookupService.resolve = function(hostname, rrtype, callback) {}

/**
 * The same as dns.resolve(), but only for IPv4 queries (A records).
 * @param hostname
 * @param callback
 */
lookupService.resolve4 = function(hostname, callback) {}

/**
 * The same as dns.resolve4() except for IPv6 queries (an AAAA query).
 * @param hostname
 * @param callback
 */
lookupService.resolve6 = function(hostname, callback) {}

/**
 * The same as dns.resolve(), but only for mail exchange queries (MX
 * records).
 * @param hostname
 * @param callback
 */
lookupService.resolveMx = function(hostname, callback) {}

/**
 * The same as dns.resolve(), but only for text queries (TXT records).
 * @param hostname
 * @param callback
 */
lookupService.resolveTxt = function(hostname, callback) {}

/**
 * The same as dns.resolve(), but only for service records (SRV records).
 * @param hostname
 * @param callback
 */
lookupService.resolveSrv = function(hostname, callback) {}

/**
 * The same as dns.resolve(), but only for start of authority record
 * queries (SOA record).
 * @param hostname
 * @param callback
 */
lookupService.resolveSoa = function(hostname, callback) {}

/**
 * The same as dns.resolve(), but only for name server records (NS
 * records).
 * @param hostname
 * @param callback
 */
lookupService.resolveNs = function(hostname, callback) {}

/**
 * The same as dns.resolve(), but only for canonical name records (CNAME
 * records). addresses is an array of the canonical name records available
 * for hostname (e.g., [&#39;bar.example.com&#39;]).
 * @param hostname
 * @param callback
 */
lookupService.resolveCname = function(hostname, callback) {}

/**
 * Reverse resolves an ip address to an array of hostnames.
 * @param ip
 * @param callback
 */
lookupService.reverse = function(ip, callback) {}

/**
 * Returns an array of IP addresses as strings that are currently being
 * used for resolution
 * @returns {Array} an array of IP addresses as strings that are currently being used for resolution
 */
lookupService.getServers = function() {}

/**
 * Given an array of IP addresses as strings, set them as the servers to
 * use for resolving
 * @param servers
 */
lookupService.setServers = function(servers) {}

exports = dns;

