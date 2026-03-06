import datetime
import dateutil.parser
import pytest

def certificate_info(server, certificate):
    openssl_result = server.run(f"openssl x509 -in {certificate} -noout -enddate -dateopt iso_8601 -subject -issuer")
    return dict([x.split('=', 1) for x in openssl_result.stdout.splitlines()])

def key_info(server, key):
    """Get key algorithm information (RSA or EC)"""
    openssl_result = server.run(f"openssl pkey -in {key} -text -noout | head -1")
    return openssl_result.stdout.strip()

@pytest.mark.parametrize("certificate_type", ['ca_certificate', 'server_certificate', 'client_certificate', 'localhost_certificate'])
def test_certificate_expiry(server, certificates, certificate_type):
    openssl_data = certificate_info(server, certificates[certificate_type])
    not_after = dateutil.parser.parse(openssl_data['notAfter'])
    now = datetime.datetime.now(tz=not_after.tzinfo)
    assert not_after - now > datetime.timedelta(days=365*10)

@pytest.mark.parametrize("key_type", ['ca_key', 'server_key', 'client_key', 'localhost_key'])
def test_key_algorithm(server, certificates, certificates_key_type, key_type):
    """Verify that the key algorithm matches the configuration (RSA or EC)"""
    key_path = certificates[key_type]
    key_algorithm = key_info(server, key_path)

    # Validate that the key type matches the configured type
    if certificates_key_type == 'rsa':
        assert 'RSA' in key_algorithm, f"Expected RSA key but got: {key_algorithm} in {key_path}"
    elif certificates_key_type == 'ec':
        assert 'EC' in key_algorithm, f"Expected EC key but got: {key_algorithm} in {key_path}"
    else:
        pytest.fail(f"Unknown configured key type: {certificates_key_type}")
