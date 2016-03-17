/**
 */
var crypto = {};

/**
 * The class for creating hash digests of data.
 * @constructor
 */
crypto.Hash = function() {}

/**
 * Updates the hash content with the given data, the encoding of which is
 * given in input_encoding and can be &#39;utf8&#39;, &#39;ascii&#39; or
 * &#39;binary&#39;. If no encoding is provided and the input is a string
 * an encoding of &#39;binary&#39; is enforced. If data is a Buffer then
 * input_encoding is ignored.
 * @param data
 * @param input_encoding
 */
crypto.Hash.prototype.update = function(data, input_encoding) {}

/**
 * Calculates the digest of all of the passed data to be hashed. The
 * encoding can be &#39;hex&#39;, &#39;binary&#39; or &#39;base64&#39;. If
 * no encoding is provided, then a buffer is returned.
 * @param encoding
 */
crypto.Hash.prototype.digest = function(encoding) {}

/**
 * Creates and returns a cipher object, with the given algorithm and
 * password.
 * @param algorithm
 * @param password
 * @returns {crypto.Cipher}
 */
crypto.createCipher = function(algorithm, password) {}

/**
 * Creates and returns a hmac object, a cryptographic hmac with the given
 * algorithm and key.
 * @param algorithm
 * @param key
 * @returns {crypto.Hmac}
 */
crypto.createHmac = function(algorithm, key) {}

/**
 * Class for verifying signatures.
 * @constructor
 */
crypto.Verify = function() {}

/**
 * Verifies the signed data by using the object and signature.
 * @param object
 * @param signature
 * @param signature_format='binary' {String}
 */
crypto.Verify.prototype.verify = function(object, signature, signature_format) {}

/**
 * Updates the verifier object with data. This can be called many times
 * with new data as it is streamed.
 * @param data
 */
crypto.Verify.prototype.update = function(data) {}

/**
 * Creates a credentials object, with the optional details being a
 * dictionary with keys:
 * @param details
 * @returns a credentials object, with the optional details being a dictionary with keys:
 */
crypto.createCredentials = function(details) {}

/**
 * Creates and returns a signing object, with the given algorithm. On
 * recent OpenSSL releases, openssl list-public-key-algorithms will display
 * the available signing algorithms. Examples are &#39;RSA-SHA256&#39;.
 * @param algorithm
 * @returns {crypto.Signer}
 */
crypto.createSign = function(algorithm) {}

/**
 * Class for encrypting data.
 * @constructor
 */
crypto.Cipher = function() {}

/**
 * Updates the cipher with data, the encoding of which is given in
 * input_encoding and can be &#39;utf8&#39;, &#39;ascii&#39; or
 * &#39;binary&#39;. If no encoding is provided, then a buffer is expected.
 * @param data
 * @param input_encoding
 * @param output_encoding
 */
crypto.Cipher.prototype.update = function(data, input_encoding, output_encoding) {}

/**
 * Returns any remaining enciphered contents, with output_encoding being
 * one of: &#39;binary&#39;, &#39;base64&#39; or &#39;hex&#39;. If no
 * encoding is provided, then a buffer is returned.
 * @param output_encoding
 * @returns any remaining enciphered contents, with output_encoding being one of: &#39;binary&#39;, &#39;base64&#39; or &#39;hex&#39;
 */
crypto.Cipher.prototype.final = function(output_encoding) {}

/**
 * For authenticated encryption modes (currently supported: GCM), this
 * method returns a Buffer that represents the authentication tag that has
 * been computed from the given data. Should be called after encryption has
 * been completed using the final method!
 */
crypto.Cipher.prototype.getAuthTag = function() {}

/**
 * For authenticated encryption modes (currently supported: GCM), this
 * method sets the value used for the additional authenticated data (AAD)
 * input parameter.
 * @param buffer
 */
crypto.Cipher.prototype.setAAD = function(buffer) {}

/**
 * You can disable automatic padding of the input data to block size. If
 * auto_padding is false, the length of the entire input data must be a
 * multiple of the cipher&#39;s block size or final will fail. Useful for
 * non-standard padding, e.g. using 0x0 instead of PKCS padding. You must
 * call this before cipher.final.
 * @param auto_padding
 */
crypto.Cipher.prototype.setAutoPadding = function(auto_padding) {}

/**
 * Creates and returns a hash object, a cryptographic hash with the given
 * algorithm which can be used to generate hash digests.
 * @param algorithm
 * @returns {crypto.Hash}
 */
crypto.createHash = function(algorithm) {}

/**
 * Class for decrypting data.
 * @constructor
 */
crypto.Decipher = function() {}

/**
 * Updates the decipher with data, which is encoded in &#39;binary&#39;,
 * &#39;base64&#39; or &#39;hex&#39;. If no encoding is provided, then a
 * buffer is expected.
 * @param data
 * @param input_encoding='binary' {String}
 * @param output_encoding='binary' {String}
 */
crypto.Decipher.prototype.update = function(data, input_encoding, output_encoding) {}

/**
 * Returns any remaining plaintext which is deciphered, with
 * output_encoding being one of: &#39;binary&#39;, &#39;ascii&#39; or
 * &#39;utf8&#39;. If no encoding is provided, then a buffer is returned.
 * @param output_encoding
 * @returns any remaining plaintext which is deciphered, with output_encoding being one of: &#39;binary&#39;, &#39;ascii&#39; or &#39;utf8&#39;
 */
crypto.Decipher.prototype.final = function(output_encoding) {}

/**
 * For authenticated encryption modes (currently supported: GCM), this
 * method sets the value used for the additional authenticated data (AAD)
 * input parameter.
 * @param buffer
 */
crypto.Decipher.prototype.setAAD = function(buffer) {}

/**
 * For authenticated encryption modes (currently supported: GCM), this
 * method must be used to pass in the received authentication tag.
 * @param buffer
 */
crypto.Decipher.prototype.setAuthTag = function(buffer) {}

/**
 * You can disable auto padding if the data has been encrypted without
 * standard block padding to prevent decipher.final from checking and
 * removing it. Can only work if the input data&#39;s length is a multiple
 * of the ciphers block size. You must call this before streaming data to
 * decipher.update.
 * @param auto_padding
 */
crypto.Decipher.prototype.setAutoPadding = function(auto_padding) {}

/**
 * Creates and returns a decipher object, with the given algorithm and key.
 * This is the mirror of the [createCipher()][] above.
 * @param algorithm
 * @param password
 * @returns {crypto.Decipher}
 */
crypto.createDecipher = function(algorithm, password) {}

/**
 * Creates and returns a verification object, with the given algorithm.
 * @param algorithm
 * @returns {crypto.Verify}
 */
crypto.createVerify = function(algorithm) {}

/**
 * Class for creating cryptographic hmac content.
 * @constructor
 */
crypto.Hmac = function() {}

/**
 * Update the hmac content with the given data. This can be called many
 * times with new data as it is streamed.
 * @param data
 */
crypto.Hmac.prototype.update = function(data) {}

/**
 * Calculates the digest of all of the passed data to the hmac. The
 * encoding can be &#39;hex&#39;, &#39;binary&#39; or &#39;base64&#39;. If
 * no encoding is provided, then a buffer is returned.
 * @param encoding
 */
crypto.Hmac.prototype.digest = function(encoding) {}

/**
 * The default encoding to use for functions that can take either strings
 * or buffers. The default value is &#39;buffer&#39;, which makes it
 * default to using Buffer objects. This is here to make the crypto module
 * more easily compatible with legacy programs that expected
 * &#39;binary&#39; to be the default encoding.
 */
crypto.DEFAULT_ENCODING = 0;

/**
 * Creates and returns a cipher object, with the given algorithm, key and
 * iv.
 * @param algorithm
 * @param key
 * @param iv
 * @returns {crypto.Cipher}
 */
crypto.createCipheriv = function(algorithm, key, iv) {}

/**
 * Creates and returns a decipher object, with the given algorithm, key and
 * iv. This is the mirror of the [createCipheriv()][] above.
 * @param algorithm
 * @param key
 * @param iv
 * @returns {crypto.Decipher}
 */
crypto.createDecipheriv = function(algorithm, key, iv) {}

/**
 * Creates a Diffie-Hellman key exchange object and generates a prime of
 * prime_length bits and using an optional specific numeric generator.
 * @param prime_length
 * @param generator
 * @returns {crypto.DiffieHellman}
 */
crypto.createDiffieHellman = function(prime_length, generator) {}

/**
 * Creates a Diffie-Hellman key exchange object using the supplied prime
 * and an optional specific generator.
 * @param prime
 * @param prime_encoding
 * @param generator
 * @param generator_encoding
 * @returns {crypto.DiffieHellman}
 */
crypto.createDiffieHellman = function(prime, prime_encoding, generator, generator_encoding) {}

/**
 * Creates an Elliptic Curve (EC) Diffie-Hellman key exchange object using
 * a predefined curve specified by curve_name string.
 * @param curve_name
 * @returns an Elliptic Curve (EC) Diffie-Hellman key exchange object using a predefined curve specified by curve_name string
 */
crypto.createECDH = function(curve_name) {}

/**
 * The class used for working with signed public key &amp; challenges. The
 * most common usage for this series of functions is when dealing with the
 * &lt;keygen&gt; element. http://www.openssl.org/docs/apps/spkac.html
 * @constructor
 */
crypto.Certificate = function() {}

/**
 * Returns true of false based on the validity of the SPKAC.
 * @param spkac
 * @returns true of false based on the validity of the SPKAC
 */
crypto.Certificate.prototype.verifySpkac = function(spkac) {}

/**
 * Exports the encoded public key from the supplied SPKAC.
 * @param spkac
 */
crypto.Certificate.prototype.exportChallenge = function(spkac) {}

/**
 * Exports the encoded challenge associated with the SPKAC.
 * @param spkac
 */
crypto.Certificate.prototype.exportPublicKey = function(spkac) {}

/**
 * The class for creating Diffie-Hellman key exchanges.
 * @constructor
 */
crypto.DiffieHellman = function() {}

/**
 * Generates private and public Diffie-Hellman key values, and returns the
 * public key in the specified encoding. This key should be transferred to
 * the other party. Encoding can be &#39;binary&#39;, &#39;hex&#39;, or
 * &#39;base64&#39;. If no encoding is provided, then a buffer is returned.
 * @param encoding
 */
crypto.DiffieHellman.prototype.generateKeys = function(encoding) {}

/**
 * Computes the shared secret using other_public_key as the other
 * party&#39;s public key and returns the computed shared secret. Supplied
 * key is interpreted using specified input_encoding, and secret is encoded
 * using specified output_encoding. Encodings can be &#39;binary&#39;,
 * &#39;hex&#39;, or &#39;base64&#39;. If the input encoding is not
 * provided, then a buffer is expected.
 * @param other_public_key
 * @param input_encoding='binary' {String}
 * @param output_encoding
 */
crypto.DiffieHellman.prototype.computeSecret = function(other_public_key, input_encoding, output_encoding) {}

/**
 * Returns the Diffie-Hellman prime in the specified encoding, which can be
 * &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If no encoding is
 * provided, then a buffer is returned.
 * @param encoding='binary' {String}
 * @returns the Diffie-Hellman prime in the specified encoding, which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;
 */
crypto.DiffieHellman.prototype.getPrime = function(encoding) {}

/**
 * Returns the Diffie-Hellman generator in the specified encoding, which
 * can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If no
 * encoding is provided, then a buffer is returned.
 * @param encoding='binary' {String}
 * @returns the Diffie-Hellman generator in the specified encoding, which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;
 */
crypto.DiffieHellman.prototype.getGenerator = function(encoding) {}

/**
 * Returns the Diffie-Hellman public key in the specified encoding, which
 * can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If no
 * encoding is provided, then a buffer is returned.
 * @param encoding='binary' {String}
 * @returns the Diffie-Hellman public key in the specified encoding, which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;
 */
crypto.DiffieHellman.prototype.getPublicKey = function(encoding) {}

/**
 * Returns the Diffie-Hellman private key in the specified encoding, which
 * can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If no
 * encoding is provided, then a buffer is returned.
 * @param encoding='binary' {String}
 * @returns the Diffie-Hellman private key in the specified encoding, which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;
 */
crypto.DiffieHellman.prototype.getPrivateKey = function(encoding) {}

/**
 * Sets the Diffie-Hellman public key. Key encoding can be
 * &#39;binary&#39;, &#39;hex&#39; or &#39;base64&#39;. If no encoding is
 * provided, then a buffer is expected.
 * @param public_key
 * @param encoding='binary' {String}
 */
crypto.DiffieHellman.prototype.setPublicKey = function(public_key, encoding) {}

/**
 * Sets the Diffie-Hellman private key. Key encoding can be
 * &#39;binary&#39;, &#39;hex&#39; or &#39;base64&#39;. If no encoding is
 * provided, then a buffer is expected.
 * @param private_key
 * @param encoding='binary' {String}
 */
crypto.DiffieHellman.prototype.setPrivateKey = function(private_key, encoding) {}

/**
 * A bit field containing any warnings and/or errors as a result of a check
 * performed during initialization. The following values are valid for this
 * property (defined in constants module):
 */
crypto.DiffieHellman.prototype.verifyError = 0;

/**
 * The class for creating EC Diffie-Hellman key exchanges.
 * @constructor
 */
crypto.ECDH = function() {}

/**
 * Generates private and public EC Diffie-Hellman key values, and returns
 * the public key in the specified format and encoding. This key should be
 * transferred to the other party.
 * @param encoding
 * @param format]
 */
crypto.ECDH.prototype.generateKeys = function(encoding, format]) {}

/**
 * Computes the shared secret using other_public_key as the other
 * party&#39;s public key and returns the computed shared secret. Supplied
 * key is interpreted using specified input_encoding, and secret is encoded
 * using specified output_encoding. Encodings can be &#39;binary&#39;,
 * &#39;hex&#39;, or &#39;base64&#39;. If the input encoding is not
 * provided, then a buffer is expected.
 * @param other_public_key
 * @param input_encoding
 * @param output_encoding
 */
crypto.ECDH.prototype.computeSecret = function(other_public_key, input_encoding, output_encoding) {}

/**
 * Returns the EC Diffie-Hellman public key in the specified encoding and
 * format.
 * @param encoding
 * @param format]
 * @returns the EC Diffie-Hellman public key in the specified encoding and format
 */
crypto.ECDH.prototype.getPublicKey = function(encoding, format]) {}

/**
 * Returns the EC Diffie-Hellman private key in the specified encoding,
 * which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If no
 * encoding is provided, then a buffer is returned.
 * @param encoding
 * @returns the EC Diffie-Hellman private key in the specified encoding, which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;
 */
crypto.ECDH.prototype.getPrivateKey = function(encoding) {}

/**
 * Sets the EC Diffie-Hellman public key. Key encoding can be
 * &#39;binary&#39;, &#39;hex&#39; or &#39;base64&#39;. If no encoding is
 * provided, then a buffer is expected.
 * @param public_key
 * @param encoding
 */
crypto.ECDH.prototype.setPublicKey = function(public_key, encoding) {}

/**
 * Sets the EC Diffie-Hellman private key. Key encoding can be
 * &#39;binary&#39;, &#39;hex&#39; or &#39;base64&#39;. If no encoding is
 * provided, then a buffer is expected.
 * @param private_key
 * @param encoding
 */
crypto.ECDH.prototype.setPrivateKey = function(private_key, encoding) {}

/**
 * Class for generating signatures.
 * @constructor
 */
crypto.Sign = function() {}

/**
 * Updates the sign object with data. This can be called many times with
 * new data as it is streamed.
 * @param data
 */
crypto.Sign.prototype.update = function(data) {}

/**
 * Calculates the signature on all the updated data passed through the
 * sign.
 * @param private_key
 * @param output_format
 */
crypto.Sign.prototype.sign = function(private_key, output_format) {}

/**
 * Returns an array with the names of the supported ciphers.
 * @returns an array with the names of the supported ciphers
 */
crypto.getCiphers = function() {}

/**
 * Creates a predefined Diffie-Hellman key exchange object. The supported
 * groups are: &#39;modp1&#39;, &#39;modp2&#39;, &#39;modp5&#39; (defined
 * in [RFC 2412][]) and &#39;modp14&#39;, &#39;modp15&#39;,
 * &#39;modp16&#39;, &#39;modp17&#39;, &#39;modp18&#39; (defined in [RFC
 * 3526][]). The returned object mimics the interface of objects created by
 * [crypto.createDiffieHellman()][] above, but will not allow to change the
 * keys (with [diffieHellman.setPublicKey()][] for example). The advantage
 * of using this routine is that the parties don&#39;t have to generate nor
 * exchange group modulus beforehand, saving both processor and
 * communication time.
 * @param group_name
 * @returns a predefined Diffie-Hellman key exchange object
 */
crypto.getDiffieHellman = function(group_name) {}

/**
 * Returns an array with the names of the supported hash algorithms.
 * @returns an array with the names of the supported hash algorithms
 */
crypto.getHashes = function() {}

/**
 * Asynchronous PBKDF2 function. Applies the selected HMAC digest function
 * (default: SHA1) to derive a key of the requested length from the
 * password, salt and number of iterations. The callback gets two
 * arguments:
 * @param password
 * @param salt
 * @param iterations
 * @param keylen
 * @param digest
 * @param callback
 */
crypto.pbkdf2 = function(password, salt, iterations, keylen, digest, callback) {}

/**
 * Synchronous PBKDF2 function. Returns derivedKey or throws error.
 * @param password
 * @param salt
 * @param iterations
 * @param keylen
 * @param digest
 * @returns derivedKey or throws error
 */
crypto.pbkdf2Sync = function(password, salt, iterations, keylen, digest) {}

/**
 * Decrypts buffer with private_key.
 * @param private_key
 * @param buffer
 */
crypto.privateDecrypt = function(private_key, buffer) {}

/**
 * Generates non-cryptographically strong pseudo-random data. The data
 * returned will be unique if it is sufficiently long, but is not
 * necessarily unpredictable. For this reason, the output of this function
 * should never be used where unpredictability is important, such as in the
 * generation of encryption keys.
 * @param size
 * @param callback
 */
crypto.pseudoRandomBytes = function(size, callback) {}

/**
 * Encrypts buffer with public_key. Only RSA is currently supported.
 * @param public_key
 * @param buffer
 */
crypto.publicEncrypt = function(public_key, buffer) {}

/**
 * Generates cryptographically strong pseudo-random data. Usage:
 * @param size
 * @param callback
 */
crypto.randomBytes = function(size, callback) {}

/**
 * Load and set engine for some/all OpenSSL functions (selected by flags).
 * @param engine
 * @param flags
 */
crypto.setEngine = function(engine, flags) {}

exports = crypto;

