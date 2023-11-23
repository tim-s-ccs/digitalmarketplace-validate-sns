import base64
import datetime

from io import BytesIO

from oscrypto.asymmetric import load_private_key, rsa_pkcs1v15_sign

from unittest import TestCase, mock

from dm_validate_sns.validate import SignatureValidator, ValidationError, validate as _validate_fn

PRIVATE_KEY = b"""
-----BEGIN PRIVATE KEY-----
MIICeAIBADANBgkqhkiG9w0BAQEFAASCAmIwggJeAgEAAoGBAK+LkCvEsnMUws8s
G5iQ8eDwCCtYBRaED8DmCOrZASJhUcijlZl2vFwx1Vo551ZJVw06zHjy04psRQ1r
0wctmU2330u4OofwduLh2jpt4sH5EUzJkEkAuJdHIv0M3fvsHOZbZPogc2ptwhTL
kSTtT75w9+A+HYRHiqIE5KIbugBlAgMBAAECgYEAjDGGYx4EcdnLts5//3kKYtzv
eUYjUhcHycMsrfm+aSmVugnCqLvltC9sN1F1CjkqF3u03ob3IF5VS2GoN9xXyCDR
KTsTMS5Duqg4Fq/Yj79lVqUbU9ukZRqQ/ijDulLT6Su4JP74354qYPuljQ3Amh8S
45Thscii8iA/gdFl5wUCQQDm4cNS2V3e8KnYMZCG4MLrENeiMmsuwQsbU0d8TbSA
7Tpw8gTDPksYzpEjFHs0P2WvaQeY/cmcnTuopIqLzqG3AkEAwqShWsc8wWWzoDnA
YzLkAHFnoKESVQezEiqYAig6b0xuhz6QvzGAAYqyAweyT3M3xD+DSjwH/uuRGn/4
fSm+wwJAbEi8RBIgXZw//F6aqzelE3xtteuxq1bsr58qatlC7CjW/Pv1UeDYdcUD
+xDzC7kkJtW6s31r3mE8BsdNF28NFwJBAIDxv1L8GmukjFLg72rIE/OXLSdkjVh3
OVIXlYwYSl3hLHe8IvgGOt7KmxMWzjGECrWfvcI38rQWKpJ7pIqGVTECQQDFhYhp
4+lb7f70593XHzBlasvoO6RJQODxsHSLnD1z3uMiMMbw1PdDG389vgS+eqs4eAi3
WxsygMAWNvSfb6/R
-----END PRIVATE KEY-----
""".strip()

CERT = b"""
-----BEGIN CERTIFICATE-----
MIIB6DCCAVGgAwIBAgIJAJvkgfs3SdauMA0GCSqGSIb3DQEBCwUAMA0xCzAJBgNV
BAYTAlVLMB4XDTE1MTAzMDA5NDYzNloXDTM1MTIzMTA5NDYzNlowDTELMAkGA1UE
BhMCVUswgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAK+LkCvEsnMUws8sG5iQ
8eDwCCtYBRaED8DmCOrZASJhUcijlZl2vFwx1Vo551ZJVw06zHjy04psRQ1r0wct
mU2330u4OofwduLh2jpt4sH5EUzJkEkAuJdHIv0M3fvsHOZbZPogc2ptwhTLkSTt
T75w9+A+HYRHiqIE5KIbugBlAgMBAAGjUDBOMB0GA1UdDgQWBBQcJiFgx5ilZpSB
9WdN0nIs2O4EnzAfBgNVHSMEGDAWgBQcJiFgx5ilZpSB9WdN0nIs2O4EnzAMBgNV
HRMEBTADAQH/MA0GCSqGSIb3DQEBCwUAA4GBADquYDn5XJIi0Gp8Y2MwQ0F4O9N2
l0d9QZihTLI9yEUYgGqmKOy1UYLDnUAqFsw0hkxCncjk6RinKKX9zZl/AqHVQrNI
co1fh3Vc+3Fxj/hr5Ky5Bcl2IRaDhnaM34TmlSMaCyu33LRJytlGb/aZRdCCFEIB
ke2qiRJ8R2fTxwtO
-----END CERTIFICATE-----
""".strip()


class TestMixin(TestCase):
    def setUp(self):
        self.utc_now = datetime.datetime(2015, 1, 1, 0, 0, 0, 0)

        self.validate_kwargs = {}

        self.message = {
            "SigningCertURL": "https://sns.us-east-1.amazonaws.com/cert.pem",
            "Timestamp": self.serialize_datetime(self.utc_now),
            "Signature": "",
            "SignatureVersion": "1",
            "Type": "Notification",
            "Message": "Hi",
            "MessageId": "123",
            "TopicArn": "arn:aws:sn:us-east-1:345:MyTopic",
        }

        self.signing_certs = {
            "https://sns.us-east-1.amazonaws.com/cert.pem": CERT,
            "https://sns.us-east-1.amazonaws.com.cn/cert.pem": CERT
        }

    def validate(self):
        if isinstance(self.message, dict):
            certificate = self.signing_certs.get(self.message.get("SigningCertURL"))
        else:
            certificate = None

        with mock.patch("dm_validate_sns.validate.urlopen") as mock_urlopen:
            if certificate:
                if isinstance(certificate, str):
                    certificate = certificate.encode()
                mock_urlopen.return_value = BytesIO(certificate)
            else:
                mock_urlopen.side_effect = NotImplementedError("Shouldn't happen")

            real_datetime = datetime.datetime
            with mock.patch("datetime.datetime") as mock_datetime:
                mock_datetime.strptime.side_effect = real_datetime.strptime
                mock_datetime.utcnow.return_value = self.utc_now

                _validate_fn(self.message, **self.validate_kwargs)

    def sign_message(self):
        self.message["Signature"] = self.get_message_signature()

    def get_message_signature(self):
        if not isinstance(self.message, dict):
            raise ValueError("Can't sign non-dict messages")

        private_key = load_private_key(PRIVATE_KEY)
        signing_content = SignatureValidator("")._get_signing_content(self.message)
        signature = rsa_pkcs1v15_sign(private_key, signing_content.encode(), "sha1")

        return base64.b64encode(signature)

    def serialize_datetime(self, dt):
        return dt.strftime("%Y-%m-%dT%H:%M:%S.{}Z".format(dt.strftime("%f")[:3]))


class TestValidate(TestMixin):
    def test_invalid_max_age_parameter(self):
        self.validate_kwargs["max_age"] = 5
        with self.assertRaisesRegex(ValueError, r"^max_age must be None or a timedelta object$"):
            self.validate()

    def test_non_dict_message(self):
        self.message = []
        with self.assertRaisesRegex(ValidationError, r"^Unexpected message type .*$"):
            self.validate()


class TestSigningCertURLValidator(TestMixin):
    def test_valid_com_signing_cert_url(self):
        self.message["SigningCertURL"] = "https://sns.us-east-1.amazonaws.com/cert.pem"
        self.sign_message()
        self.validate()

    def test_valid_com_cn_signing_cert_url(self):
        self.message["SigningCertURL"] = "https://sns.us-east-1.amazonaws.com.cn/cert.pem"
        self.sign_message()
        self.validate()

    def test_non_aws_signing_cert_url(self):
        self.message["SigningCertURL"] = "https://example.com/cert.pem"
        with self.assertRaisesRegex(ValidationError, r"^SigningCertURL .* doesn't match required format .*"):
            self.validate()

    def test_non_aws_controlled_signing_cert_url(self):
        self.message["SigningCertURL"] = "https://s3.us-east-1.amazonaws.com/evil/cert.pem"
        with self.assertRaisesRegex(ValidationError, r"^SigningCertURL .* doesn't match required format .*"):
            self.validate()

    def test_missing_signing_cert_url(self):
        del self.message["SigningCertURL"]
        with self.assertRaisesRegex(ValidationError, r"^SigningCertURL .* doesn't match required format .*"):
            self.validate()

    def test_non_string_signing_cert_url(self):
        self.message["SigningCertURL"] = 123
        with self.assertRaisesRegex(ValidationError, r"^SigningCertURL .* doesn't match required format .*"):
            self.validate()


class TestMessageAgeValidator(TestMixin):
    def test_valid_age(self):
        self.message["Timestamp"] = self.serialize_datetime(self.utc_now)
        self.sign_message()
        self.validate()

    def test_nearly_too_old(self):
        self.message["Timestamp"] = self.serialize_datetime(self.utc_now - datetime.timedelta(hours=1))
        self.sign_message()
        self.validate()

    def test_too_old(self):
        self.message["Timestamp"] = self.serialize_datetime(self.utc_now - datetime.timedelta(hours=1, seconds=1))
        with self.assertRaisesRegex(ValidationError, r"^Message is too old: .*$"):
            self.validate()

    def test_missing_timestamp(self):
        del self.message["Timestamp"]
        with self.assertRaisesRegex(ValidationError, r"^Expected Timestamp to be a string, but received .*$"):
            self.validate()

    def test_non_string_timestamp(self):
        self.message["Timestamp"] = 123
        with self.assertRaisesRegex(ValidationError, r"^Expected Timestamp to be a string, but received .*$"):
            self.validate()

    def test_unexpected_timestamp_format(self):
        self.message["Timestamp"] = "January 5 2015"
        with self.assertRaisesRegex(ValidationError, r"^Unexpected Timestamp format .*$"):
            self.validate()


class TestSignatureValidator(TestMixin):
    def test_missing_signature_version(self):
        del self.message["SignatureVersion"]
        with self.assertRaisesRegex(ValidationError, r"^Unexpected SignatureVersion .*$"):
            self.validate()

    def test_unexpected_signature_version(self):
        self.message["SignatureVersion"] = "99"
        with self.assertRaisesRegex(ValidationError, r"^Unexpected SignatureVersion .*$"):
            self.validate()

    def test_valid_signature(self):
        self.sign_message()
        self.validate()

    def test_missing_signature(self):
        del self.message["Signature"]
        with self.assertRaisesRegex(ValidationError, r"^Expected Signature to be a string, but received .*$"):
            self.validate()

    def test_non_string_signature(self):
        self.message["Signature"] = 99
        with self.assertRaisesRegex(ValidationError, r"^Expected Signature to be a string, but received .*$"):
            self.validate()

    def test_non_base64_signature(self):
        self.message["Signature"] = "!!!???"
        with self.assertRaisesRegex(ValidationError, r"^Invalid signature$"):
            self.validate()

    def test_unsigned_message(self):
        with self.assertRaisesRegex(ValidationError, r"^Invalid signature$"):
            self.validate()

    def test_invalid_signature(self):
        self.sign_message()
        self.message["Signature"] = self.message["Signature"].swapcase()
        with self.assertRaisesRegex(ValidationError, r"^Invalid signature$"):
            self.validate()

    def test_valid_signature_with_unicode_certificate(self):
        self.signing_certs = {
            "https://sns.us-east-1.amazonaws.com/cert.pem": CERT.decode(),
            "https://sns.us-east-1.amazonaws.com.cn/cert.pem": CERT.decode()
        }

        self.sign_message()
        self.validate()
