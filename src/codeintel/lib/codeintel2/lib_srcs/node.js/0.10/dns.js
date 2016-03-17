/**
 * Use require(&#39;dns&#39;) to access this module.
 */
var dns = {};

/**
 * Resolves a domain (e.g. &#39;google.com&#39;) into an array of the
 * record types specified by rrtype. Valid rrtypes are &#39;A&#39; (IPV4
 * addresses, default), &#39;AAAA&#39; (IPV6 addresses), &#39;MX&#39; (mail
 * exchange records), &#39;TXT&#39; (text records), &#39;SRV&#39; (SRV
 * records), &#39;PTR&#39; (used for reverse IP lookups), &#39;NS&#39;
 * (name server records) and &#39;CNAME&#39; (canonical name records).
 * @param domain
 * @param rrtype
 * @param callback
 */
dns.resolve = function(domain, rrtype, callback) {}

/**
 * Reverse resolves an ip address to an array of domain names.
 * @param ip
 * @param callback
 */
dns.reverse = function(ip, callback) {}

/**
 * The same as dns.resolve(), but only for mail exchange queries (MX
 * records).
 * @param domain
 * @param callback
 */
dns.resolveMx = function(domain, callback) {}

/**
 * The same as dns.resolve(), but only for text queries (TXT records).
 * @param domain
 * @param callback
 */
dns.resolveTxt = function(domain, callback) {}

/**
 * The same as dns.resolve(), but only for IPv4 queries (A records).
 * @param domain
 * @param callback
 */
dns.resolve4 = function(domain, callback) {}

/**
 * The same as dns.resolve(), but only for service records (SRV records).
 * @param domain
 * @param callback
 */
dns.resolveSrv = function(domain, callback) {}

/**
 * The same as dns.resolve4() except for IPv6 queries (an AAAA query).
 * @param domain
 * @param callback
 */
dns.resolve6 = function(domain, callback) {}

/**
 * Resolves a domain (e.g. &#39;google.com&#39;) into the first found A
 * (IPv4) or AAAA (IPv6) record.
 * @param domain
 * @param family
 * @param callback
 */
dns.lookup = function(domain, family, callback) {}

/**
 * The same as dns.resolve(), but only for canonical name records (CNAME
 * records). addresses is an array of the canonical name records available
 * for domain (e.g., [&#39;bar.example.com&#39;]).
 * @param domain
 * @param callback
 */
dns.resolveCname = function(domain, callback) {}

/**
 * The same as dns.resolve(), but only for name server records (NS
 * records).
 * @param domain
 * @param callback
 */
dns.resolveNs = function(domain, callback) {}

exports = dns;

