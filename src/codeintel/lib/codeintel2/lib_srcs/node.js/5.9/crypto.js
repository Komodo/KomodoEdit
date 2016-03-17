/**
 * The crypto module provides cryptographic functionality that includes a
 * set of wrappers for OpenSSL&#39;s hash, HMAC, cipher, decipher, sign and
 * verify functions.
 */
var crypto = {};

/**
 * The Hash class is a utility for creating hash digests of data. It can be
 * used in one of two ways:
 * @constructor
 */
crypto.Hash = function() {}

/**
 * Updates the hash content with the given data, the encoding of which is
 * given in input_encoding and can be &#39;utf8&#39;, &#39;ascii&#39; or
 * &#39;binary&#39;. If encoding is not provided, and the data is a string,
 * an encoding of &#39;binary&#39; is enforced. If data is a [Buffer][]
 * then input_encoding is ignored.
 * @param data
 * @param input_encoding
 */
crypto.Hash.prototype.update = function(data, input_encoding) {}

/**
 * Calculates the digest of all of the data passed to be hashed (using the
 * [hash.update()][] method). The encoding can be &#39;hex&#39;,
 * &#39;binary&#39; or &#39;base64&#39;. If encoding is provided a string
 * will be returned; otherwise a [Buffer][] is returned.
 * @param encoding
 */
crypto.Hash.prototype.digest = function(encoding) {}

/**
 * The Verify class is a utility for verifying signatures. It can be used
 * in one of two ways:
 * @constructor
 */
crypto.Verify = function() {}

/**
 * Verifies the provided data using the given object and signature.
 * @param object
 * @param signature
 * @param signature_format='binary' {String}
 */
crypto.Verify.prototype.verify = function(object, signature, signature_format) {}

/**
 * Updates the verifier object with the given data. This can be called many
 * times with new data as it is streamed.
 * @param data
 */
crypto.Verify.prototype.update = function(data) {}

/**
 * Instances of the Cipher class are used to encrypt data. The class can be
 * used in one of two ways:
 * @constructor
 */
crypto.Cipher = function() {}

/**
 * Updates the cipher with data. If the input_encoding argument is given,
 * it&#39;s value must be one of &#39;utf8&#39;, &#39;ascii&#39;, or
 * &#39;binary&#39; and the data argument is a string using the specified
 * encoding. If the input_encoding argument is not given, data must be a
 * [Buffer][]. If data is a [Buffer][] then input_encoding is ignored.
 * @param data
 * @param input_encoding
 * @param output_encoding
 */
crypto.Cipher.prototype.update = function(data, input_encoding, output_encoding) {}

/**
 * Returns any remaining enciphered contents. If output_encoding parameter
 * is one of &#39;binary&#39;, &#39;base64&#39; or &#39;hex&#39;, a string
 * is returned.
 * @param output_encoding
 * @returns any remaining enciphered contents
 */
crypto.Cipher.prototype.final = function(output_encoding) {}

/**
 * When using an authenticated encryption mode (only GCM is currently
 * supported), the cipher.getAuthTag() method returns a [Buffer][]
 * containing the authentication tag that has been computed from the given
 * data.
 */
crypto.Cipher.prototype.getAuthTag = function() {}

/**
 * When using an authenticated encryption mode (only GCM is currently
 * supported), the cipher.setAAD() method sets the value used for the
 * additional authenticated data (AAD) input parameter.
 * @param buffer
 */
crypto.Cipher.prototype.setAAD = function(buffer) {}

/**
 * When using block encryption algorithms, the Cipher class will
 * automatically add padding to the input data to the appropriate block
 * size. To disable the default padding call cipher.setAutoPadding(false).
 * @param auto_padding
 */
crypto.Cipher.prototype.setAutoPadding = function(auto_padding) {}

/**
 * Instances of the Decipher class are used to decrypt data. The class can
 * be used in one of two ways:
 * @constructor
 */
crypto.Decipher = function() {}

/**
 * Updates the decipher with data. If the input_encoding argument is given,
 * it&#39;s value must be one of &#39;binary&#39;, &#39;base64&#39;, or
 * &#39;hex&#39; and the data argument is a string using the specified
 * encoding. If the input_encoding argument is not given, data must be a
 * [Buffer][]. If data is a [Buffer][] then input_encoding is ignored.
 * @param data
 * @param input_encoding='binary' {String}
 * @param output_encoding='binary' {String}
 */
crypto.Decipher.prototype.update = function(data, input_encoding, output_encoding) {}

/**
 * Returns any remaining deciphered contents. If output_encoding parameter
 * is one of &#39;binary&#39;, &#39;base64&#39; or &#39;hex&#39;, a string
 * is returned.
 * @param output_encoding
 * @returns any remaining deciphered contents
 */
crypto.Decipher.prototype.final = function(output_encoding) {}

/**
 * When using an authenticated encryption mode (only GCM is currently
 * supported), the cipher.setAAD() method sets the value used for the
 * additional authenticated data (AAD) input parameter.
 * @param buffer
 */
crypto.Decipher.prototype.setAAD = function(buffer) {}

/**
 * When using an authenticated encryption mode (only GCM is currently
 * supported), the decipher.setAuthTag() method is used to pass in the
 * received authentication tag. If no tag is provided, or if the cipher
 * text has been tampered with, [decipher.final()][] with throw, indicating
 * that the cipher text should be discarded due to failed authentication.
 * @param buffer
 */
crypto.Decipher.prototype.setAuthTag = function(buffer) {}

/**
 * When data has been encrypted without standard block padding, calling
 * decipher.setAuthPadding(false) will disable automatic padding to prevent
 * [decipher.final()][] from checking for and removing padding.
 * @param auto_padding
 */
crypto.Decipher.prototype.setAutoPadding = function(auto_padding) {}

/**
 * The Hmac Class is a utility for creating cryptographic HMAC digests. It
 * can be used in one of two ways:
 * @constructor
 */
crypto.Hmac = function() {}

/**
 * Update the Hmac content with the given data. This can be called many
 * times with new data as it is streamed.
 * @param data
 */
crypto.Hmac.prototype.update = function(data) {}

/**
 * Calculates the HMAC digest of all of the data passed using
 * [hmac.update()][].
 * @param encoding
 */
crypto.Hmac.prototype.digest = function(encoding) {}

/**
 * SPKAC is a Certificate Signing Request mechanism originally implemented
 * by Netscape and now specified formally as part of [HTML5&#39;s keygen
 * element][].
 * @constructor
 */
crypto.Certificate = function() {}

/**
 * Instances of the Certificate class can be created using the new keyword
 * or by calling crypto.Certificate() as a function:
 */
crypto.Certificate.prototype.Certificate = function() {}

/**
 * The spkac data structure includes a public key and a challenge. The
 * certificate.exportChallenge() returns the challenge component in the
 * form of a Node.js [Buffer][]. The spkac argument can be either a string
 * or a [Buffer][].
 * @param spkac
 */
crypto.Certificate.prototype.exportChallenge = function(spkac) {}

/**
 * The spkac data structure includes a public key and a challenge. The
 * certificate.exportPublicKey() returns the public key component in the
 * form of a Node.js [Buffer][]. The spkac argument can be either a string
 * or a [Buffer][].
 * @param spkac
 */
crypto.Certificate.prototype.exportPublicKey = function(spkac) {}

/**
 * Returns true if the given spkac data structure is valid, false
 * otherwise.
 * @param spkac
 * @returns true if the given spkac data structure is valid, false otherwise
 */
crypto.Certificate.prototype.verifySpkac = function(spkac) {}

/**
 * The DiffieHellman class is a utility for creating Diffie-Hellman key
 * exchanges.
 * @constructor
 */
crypto.DiffieHellman = function() {}

/**
 * Computes the shared secret using other_public_key as the other
 * party&#39;s public key and returns the computed shared secret. The
 * supplied key is interpreted using the specified input_encoding, and
 * secret is encoded using specified output_encoding. Encodings can be
 * &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If the
 * input_encoding is not provided, other_public_key is expected to be a
 * [Buffer][].
 * @param other_public_key
 * @param input_encoding='binary' {String}
 * @param output_encoding
 */
crypto.DiffieHellman.prototype.computeSecret = function(other_public_key, input_encoding, output_encoding) {}

/**
 * Generates private and public Diffie-Hellman key values, and returns the
 * public key in the specified encoding. This key should be transferred to
 * the other party. Encoding can be &#39;binary&#39;, &#39;hex&#39;, or
 * &#39;base64&#39;. If encoding is provided a string is returned;
 * otherwise a [Buffer][] is returned.
 * @param encoding
 */
crypto.DiffieHellman.prototype.generateKeys = function(encoding) {}

/**
 * Returns the Diffie-Hellman generator in the specified encoding, which
 * can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If encoding
 * is provided a string is returned; otherwise a [Buffer][] is returned.
 * @param encoding='binary' {String}
 * @returns the Diffie-Hellman generator in the specified encoding, which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;
 */
crypto.DiffieHellman.prototype.getGenerator = function(encoding) {}

/**
 * Returns the Diffie-Hellman prime in the specified encoding, which can be
 * &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If encoding is
 * provided a string is returned; otherwise a [Buffer][] is returned.
 * @param encoding='binary' {String}
 * @returns the Diffie-Hellman prime in the specified encoding, which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;
 */
crypto.DiffieHellman.prototype.getPrime = function(encoding) {}

/**
 * Returns the Diffie-Hellman private key in the specified encoding, which
 * can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If encoding
 * is provided a string is returned; otherwise a [Buffer][] is returned.
 * @param encoding='binary' {String}
 * @returns the Diffie-Hellman private key in the specified encoding, which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;
 */
crypto.DiffieHellman.prototype.getPrivateKey = function(encoding) {}

/**
 * Returns the Diffie-Hellman public key in the specified encoding, which
 * can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If encoding
 * is provided a string is returned; otherwise a [Buffer][] is returned.
 * @param encoding='binary' {String}
 * @returns the Diffie-Hellman public key in the specified encoding, which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;
 */
crypto.DiffieHellman.prototype.getPublicKey = function(encoding) {}

/**
 * Sets the Diffie-Hellman private key. If the encoding argument is
 * provided and is either &#39;binary&#39;, &#39;hex&#39;, or
 * &#39;base64&#39;, private_key is expected to be a string. If no encoding
 * is provided, private_key is expected to be a [Buffer][].
 * @param private_key
 * @param encoding='binary' {String}
 */
crypto.DiffieHellman.prototype.setPrivateKey = function(private_key, encoding) {}

/**
 * Sets the Diffie-Hellman public key. If the encoding argument is provided
 * and is either &#39;binary&#39;, &#39;hex&#39; or &#39;base64&#39;,
 * public_key is expected to be a string. If no encoding is provided,
 * public_key is expected to be a [Buffer][].
 * @param public_key
 * @param encoding='binary' {String}
 */
crypto.DiffieHellman.prototype.setPublicKey = function(public_key, encoding) {}

/**
 * A bit field containing any warnings and/or errors resulting from a check
 * performed during initialization of the DiffieHellman object.
 */
crypto.DiffieHellman.prototype.verifyError = 0;

/**
 * The ECDH class is a utility for creating Elliptic Curve Diffie-Hellman
 * (ECDH) key exchanges.
 * @constructor
 */
crypto.ECDH = function() {}

/**
 * Computes the shared secret using other_public_key as the other
 * party&#39;s public key and returns the computed shared secret. The
 * supplied key is interpreted using specified input_encoding, and the
 * returned secret is encoded using the specified output_encoding.
 * Encodings can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;.
 * If the input_encoding is not provided, other_public_key is expected to
 * be a [Buffer][].
 * @param other_public_key
 * @param input_encoding
 * @param output_encoding
 */
crypto.ECDH.prototype.computeSecret = function(other_public_key, input_encoding, output_encoding) {}

/**
 * Generates private and public EC Diffie-Hellman key values, and returns
 * the public key in the specified format and encoding. This key should be
 * transferred to the other party.
 * @param encoding
 * @param format
 */
crypto.ECDH.prototype.generateKeys = function(encoding, format) {}

/**
 * Returns the EC Diffie-Hellman private key in the specified encoding,
 * which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;. If
 * encoding is provided a string is returned; otherwise a [Buffer][] is
 * returned.
 * @param encoding
 * @returns the EC Diffie-Hellman private key in the specified encoding, which can be &#39;binary&#39;, &#39;hex&#39;, or &#39;base64&#39;
 */
crypto.ECDH.prototype.getPrivateKey = function(encoding) {}

/**
 * Returns the EC Diffie-Hellman public key in the specified encoding and
 * format.
 * @param encoding
 * @param format
 * @returns the EC Diffie-Hellman public key in the specified encoding and format
 */
crypto.ECDH.prototype.getPublicKey = function(encoding, format) {}

/**
 * Sets the EC Diffie-Hellman private key. The encoding can be
 * &#39;binary&#39;, &#39;hex&#39; or &#39;base64&#39;. If encoding is
 * provided, private_key is expected to be a string; otherwise private_key
 * is expected to be a [Buffer][]. If private_key is not valid for the
 * curve specified when the ECDH object was created, an error is thrown.
 * Upon setting the private key, the associated public point (key) is also
 * generated and set in the ECDH object.
 * @param private_key
 * @param encoding
 */
crypto.ECDH.prototype.setPrivateKey = function(private_key, encoding) {}

/**
 * Sets the EC Diffie-Hellman public key. Key encoding can be
 * &#39;binary&#39;, &#39;hex&#39; or &#39;base64&#39;. If encoding is
 * provided public_key is expected to be a string; otherwise a [Buffer][]
 * is expected.
 * @param public_key
 * @param encoding
 */
crypto.ECDH.prototype.setPublicKey = function(public_key, encoding) {}

/**
 * The Sign Class is a utility for generating signatures. It can be used in
 * one of two ways:
 * @constructor
 */
crypto.Sign = function() {}

/**
 * Calculates the signature on all the data passed through using either
 * [sign.update()][] or [sign.write()][stream-writable-write].
 * @param private_key
 * @param output_format
 */
crypto.Sign.prototype.sign = function(private_key, output_format) {}

/**
 * Updates the sign object with the given data. This can be called many
 * times with new data as it is streamed.
 * @param data
 */
crypto.Sign.prototype.update = function(data) {}

exports = crypto;

