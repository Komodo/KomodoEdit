# Pure-Python ECDSA

[![build status](https://travis-ci.org/warner/python-ecdsa.png)](http://travis-ci.org/warner/python-ecdsa)


This is an easy-to-use implementation of ECDSA cryptography (Elliptic Curve
Digital Signature Algorithm), implemented purely in Python, released under
the MIT license. With this library, you can quickly create keypairs (signing
key and verifying key), sign messages, and verify the signatures. The keys
and signatures are very short, making them easy to handle and incorporate
into other protocols.

## Features

This library provides key generation, signing, and verifying, for five
popular NIST "Suite B" GF(p) curves, with key lengths of 192, 224, 256, 384,
and 521 bits. The "short names" for these curves, as known by the OpenSSL
tool, are: prime192v1, secp224r1, prime256v1, secp384r1, and secp521r1. No
other curves are included, but it would not be too hard to add more.

## Dependencies

This library uses only Python. It requires python2.6 or later versions of the
python2.x series. It is also compatible with python3.2 and 3.3.

To run the OpenSSL compatibility tests, the 'openssl' tool must be on your
$PATH. This release has been tested successfully against both OpenSSL 0.9.8o
and 1.0.0a .

## Speed

The following table shows how long this library takes to generate keypairs
(keygen=), to sign data (sign=), and to verify those signatures (verify=), on
my 2008 Mac laptop. All times are in seconds. It also shows the length of a
signature (in bytes): the verifying ("public") key is typically the same
length as the signature, and the signing ("private") key is half that length.

* NIST192p: siglen= 48, keygen=0.160s, sign=0.058s, verify=0.116s
* NIST224p: siglen= 56, keygen=0.230s, sign=0.086s, verify=0.165s
* NIST256p: siglen= 64, keygen=0.305s, sign=0.112s, verify=0.220s
* NIST384p: siglen= 96, keygen=0.801s, sign=0.289s, verify=0.558s
* NIST521p: siglen=132, keygen=1.582s, sign=0.584s, verify=1.152s

For comparison, a quality C++ implementation of ECDSA (Crypto++) typically
computes a NIST256p signature in 2.88ms and a verification in 8.53ms, about
30-40x faster.

Keys and signature can be serialized in different ways (see Usage, below).
For a NIST192p key, the three basic representations require strings of the
following lengths (in bytes):

    to_string:  signkey= 24, verifykey= 48, signature=48
    DER:        signkey=106, verifykey= 80, signature=55
    PEM:        signkey=278, verifykey=162, (no support for PEM signatures)

## History

In 2006, Peter Pearson announced his pure-python implementation of ECDSA in a
[message to sci.crypt][1], available from his [download site][2]. In 2010,
Brian Warner wrote a wrapper around this code, to make it a bit easier and
safer to use. You are looking at the README for this wrapper.

[1]: http://www.derkeiler.com/Newsgroups/sci.crypt/2006-01/msg00651.html
[2]: http://webpages.charter.net/curryfans/peter/downloads.html

## Testing

There are four test suites, three for the original Pearson module, and one
more for the wrapper. To run them all, do this:

    python ecdsa/numbertheory.py   # look for "****" and "failed" for problems
    python ecdsa/ellipticcurve.py   # look for "Bad" for problems
    python ecdsa/ecdsa.py   # look for "****" and "failed" for problems
    python ecdsa/test_pyecdsa.py  # look for "FAILED" for problems

On my 2009 Mac laptop, the combined tests take about 34 seconds to run. On a
2.4GHz P4 Linux box, they take 81 seconds.

One component of `test_pyecdsa.py` checks compatibility with OpenSSL, by
running the "openssl" CLI tool. If this tool is not on your $PATH, you may
want to comment out this test (the easiest way is to add a line that says
"del OpenSSL" to the end of test_pyecdsa.py).

## Security

This library does not protect against timing attacks. Do not allow attackers
to measure how long it takes you to generate a keypair or sign a message.
This library depends upon a strong source of random numbers. Do not use it on
a system where os.urandom() is weak.

## Usage

You start by creating a SigningKey. You can use this to sign data, by passing
in a data string and getting back the signature (also a string). You can also
ask a SigningKey to give you the corresponding VerifyingKey. The VerifyingKey
can be used to verify a signature, by passing it both the data string and the
signature string: it either returns True or raises BadSignatureError.

    from ecdsa import SigningKey
    sk = SigningKey.generate() # uses NIST192p
    vk = sk.get_verifying_key()
    signature = sk.sign("message")
    assert vk.verify(signature, "message")

Each SigningKey/VerifyingKey is associated with a specific curve, like
NIST192p (the default one). Longer curves are more secure, but take longer to
use, and result in longer keys and signatures.

    from ecdsa import SigningKey, NIST384p
    sk = SigningKey.generate(curve=NIST384p)
    vk = sk.get_verifying_key()
    signature = sk.sign("message")
    assert vk.verify(signature, "message")

The SigningKey can be serialized into several different formats: the shortest
is to call `s=sk.to_string()`, and then re-create it with
`SigningKey.from_string(s, curve)` . This short form does not record the
curve, so you must be sure to tell from_string() the same curve you used for
the original key. The short form of a NIST192p-based signing key is just 24
bytes long.

    from ecdsa import SigningKey, NIST384p
    sk = SigningKey.generate(curve=NIST384p)
    sk_string = sk.to_string()
    sk2 = SigningKey.from_string(sk_string, curve=NIST384p)
    # sk and sk2 are the same key

`sk.to_pem()` and `sk.to_der()` will serialize the signing key into the same
formats that OpenSSL uses. The PEM file looks like the familiar ASCII-armored
`"-----BEGIN EC PRIVATE KEY-----"` base64-encoded format, and the DER format
is a shorter binary form of the same data.
`SigningKey.from_pem()/.from_der()` will undo this serialization. These
formats include the curve name, so you do not need to pass in a curve
identifier to the deserializer.

    from ecdsa import SigningKey, NIST384p
    sk = SigningKey.generate(curve=NIST384p)
    sk_pem = sk.to_pem()
    sk2 = SigningKey.from_pem(sk_pem)
    # sk and sk2 are the same key

Likewise, the VerifyingKey can be serialized in the same way:
`vk.to_string()/VerifyingKey.from_string()`, `to_pem()/from_pem()`, and
`to_der()/from_der()`. The same curve= argument is needed for
`VerifyingKey.from_string()`.

    from ecdsa import SigningKey, VerifyingKey, NIST384p
    sk = SigningKey.generate(curve=NIST384p)
    vk = sk.get_verifying_key()
    vk_string = vk.to_string()
    vk2 = VerifyingKey.from_string(vk_string, curve=NIST384p)
    # vk and vk2 are the same key

    from ecdsa import SigningKey, VerifyingKey, NIST384p
    sk = SigningKey.generate(curve=NIST384p)
    vk = sk.get_verifying_key()
    vk_pem = vk.to_pem()
    vk2 = VerifyingKey.from_pem(vk_pem)
    # vk and vk2 are the same key

There are a couple of different ways to compute a signature. Fundamentally,
ECDSA takes a number that represents the data being signed, and returns a
pair of numbers that represent the signature. The hashfunc= argument to
`sk.sign()` and `vk.verify()` is used to turn an arbitrary string into
fixed-length digest, which is then turned into a number that ECDSA can sign,
and both sign and verify must use the same approach. The default value is
hashlib.sha1, but if you use NIST256p or a longer curve, you can use
hashlib.sha256 instead.

There are also multiple ways to represent a signature. The default
`sk.sign()` and `vk.verify()` methods present it as a short string, for
simplicity and minimal overhead. To use a different scheme, use the
`sk.sign(sigencode=)` and `vk.verify(sigdecode=)` arguments. There are helper
funcions in the "ecdsa.util" module that can be useful here.

It is also possible to create a SigningKey from a "seed", which is
deterministic. This can be used in protocols where you want to derive
consistent signing keys from some other secret, for example when you want
three separate keys and only want to store a single master secret. You should
start with a uniformly-distributed unguessable seed with about curve.baselen
bytes of entropy, and then use one of the helper functions in ecdsa.util to
convert it into an integer in the correct range, and then finally pass it
into `SigningKey.from_secret_exponent()`, like this:

    from pyecdsa import NIST384p, SigningKey
    from pyecdsa.util import randrange_from_seed__trytryagain

    def make_key(seed):
      secexp = randrange_from_seed__trytryagain(seed, NIST384p.order)
      return SigningKey.from_secret_exponent(secexp, curve=NIST384p)

    seed = os.urandom(NIST384p.baselen) # or other starting point
    sk1a = make_key(seed)
    sk1b = make_key(seed)
    # note: sk1a and sk1b are the same key
    sk2 = make_key("2-"+seed)  # different key

## OpenSSL Compatibility

To produce signatures that can be verified by OpenSSL tools, or to verify
signatures that were produced by those tools, use:

    # openssl ecparam -name secp224r1 -genkey -out sk.pem
    # openssl ec -in sk.pem -pubout -out vk.pem
    # openssl dgst -ecdsa-with-SHA1 -sign sk.pem -out data.sig data
    # openssl dgst -ecdsa-with-SHA1 -verify vk.pem -signature data.sig data
    # openssl dgst -ecdsa-with-SHA1 -prverify sk.pem -signature data.sig data

    sk.sign(msg, hashfunc=hashlib.sha1, sigencode=ecdsa.util.sigencode_der)
    vk.verify(sig, msg, hashfunc=hashlib.sha1, sigdecode=ecdsa.util.sigdecode_der)

The keys that openssl handles can be read and written as follows:

    sk = SigningKey.from_pem(open("sk.pem").read())
    open("sk.pem","w").write(sk.to_pem())

    vk = VerifyingKey.from_pem(open("vk.pem").read())
    open("vk.pem","w").write(vk.to_pem())

## Entropy

Creating a signing key with `SigningKey.generate()` requires some form of
entropy (as opposed to `from_secret_exponent/from_string/from_der/from_pem`,
which are deterministic and do not require an entropy source). The default
source is `os.urandom()`, but you can pass any other function that behaves
like os.urandom as the entropy= argument to do something different. This may
be useful in unit tests, where you want to achieve repeatable results. The
ecdsa.util.PRNG utility is handy here: it takes a seed and produces a strong
pseudo-random stream from it:

    from ecdsa.util import PRNG
    from ecdsa import SigningKey
    rng1 = PRNG("seed")
    sk1 = SigningKey.generate(entropy=rng1)
    rng2 = PRNG("seed")
    sk2 = SigningKey.generate(entropy=rng2)
    # sk1 and sk2 are the same key

Likewise, ECDSA signature generation requires a random number, and each
signature must use a different one (using the same number twice will
immediately reveal the private signing key). The `sk.sign()` method takes an
entropy= argument which behaves the same as `SigningKey.generate(entropy=)`.

## Deterministic Signatures

If you call `SigningKey.sign_deterministic(data)` instead of `.sign(data)`,
the code will generate a deterministic signature instead of a random one.
This uses the algorithm from RFC6979 to safely generate a unique `k` value,
derived from the private key and the message being signed. Each time you sign
the same message with the same key, you will get the same signature (using
the same `k`).

This may become the default in a future version, as it is not vulnerable to
failures of the entropy source.

## Examples

Create a NIST192p keypair and immediately save both to disk:

    from ecdsa import SigningKey
    sk = SigningKey.generate()
    vk = sk.get_verifying_key()
    open("private.pem","w").write(sk.to_pem())
    open("public.pem","w").write(vk.to_pem())

Load a signing key from disk, use it to sign a message, and write the
signature to disk:

    from ecdsa import SigningKey
    sk = SigningKey.from_pem(open("private.pem").read())
    message = open("message","rb").read()
    sig = sk.sign(message)
    open("signature","wb").write(sig)

Load the verifying key, message, and signature from disk, and verify the
signature:

    from ecdsa import VerifyingKey, BadSignatureError
    vk = VerifyingKey.from_pem(open("public.pem").read())
    message = open("message","rb").read()
    sig = open("signature","rb").read()
    try:
      vk.verify(sig, message)
      print "good signature"
    except BadSignatureError:
      print "BAD SIGNATURE"

Create a NIST521p keypair

    from ecdsa import SigningKey, NIST521p
    sk = SigningKey.generate(curve=NIST521p)
    vk = sk.get_verifying_key()

Create three independent signing keys from a master seed:

    from pyecdsa import NIST192p, SigningKey
    from pyecdsa.util import randrange_from_seed__trytryagain

    def make_key_from_seed(seed, curve=NIST192p):
      secexp = randrange_from_seed__trytryagain(seed, curve.order)
      return SigningKey.from_secret_exponent(secexp, curve)

    sk1 = make_key_from_seed("1:%s" % seed)
    sk2 = make_key_from_seed("2:%s" % seed)
    sk3 = make_key_from_seed("3:%s" % seed)
