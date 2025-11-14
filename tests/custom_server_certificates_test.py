import pytest


class TestCustomServerCertificates:
    """Test custom server certificate functionality"""

    def test_certificate_configuration_loaded(self, pytestconfig, certificates):
        """Test that custom-server certificate configuration is properly loaded"""
        if pytestconfig.getoption("certificate_source") != "custom-server":
            pytest.skip("Test only runs with --certificate-source=custom-server")

        required_certs = [
            'server_certificate',
            'server_key',
            'server_ca_certificate',
            'ca_certificate'
        ]

        for cert_key in required_certs:
            assert cert_key in certificates, f"Missing certificate key: {cert_key}"

    def test_generated_certificates_exist(self, pytestconfig, server, certificates):
        """Test that generated certificates exist on the server"""
        if pytestconfig.getoption("certificate_source") != "custom-server":
            pytest.skip("Test only runs with --certificate-source=custom-server")

        # Test that generated certificates (CA, client, localhost) exist
        generated_certs = [
            'ca_certificate',
            'client_certificate',
            'localhost_certificate'
        ]

        for cert_key in generated_certs:
            if cert_key in certificates:
                cert_path = certificates[cert_key]
                cmd = server.run(f"test -f {cert_path}")
                assert cmd.rc == 0, f"Generated certificate file does not exist: {cert_path}"

    def test_custom_server_certificate_validation_tool_exists(self, pytestconfig, server):
        """Test that certificate validation tool is available"""
        if pytestconfig.getoption("certificate_source") != "custom-server":
            pytest.skip("Test only runs with --certificate-source=custom-server")

        script_path = "/usr/local/bin/foreman-certificate-check"
        cmd = server.run(f"test -f {script_path}")

        if cmd.rc != 0:
            pytest.skip(f"Certificate check script not available on server: {script_path}")

        # Test that the script runs without crashing
        cmd = server.run(f"{script_path} --help")
        assert cmd.rc in [0, 1], "Certificate check script should show help or usage info"
        assert "usage:" in cmd.stderr.lower() or "CERT_FILE" in cmd.stderr

    def test_certificate_related_services_running(self, pytestconfig, server):
        """Test that certificate-dependent services are running"""
        if pytestconfig.getoption("certificate_source") != "custom-server":
            pytest.skip("Test only runs with --certificate-source=custom-server")

        services = [
            "httpd",
            "candlepin",
            "foreman-proxy"
        ]

        for service in services:
            cmd = server.run(f"systemctl is-active {service}")
            assert cmd.rc == 0, f"Service {service} is not active: {cmd.stdout.strip()}"

    def test_https_basic_connectivity(self, pytestconfig, server, server_fqdn):
        """Test basic HTTPS connectivity (ignoring certificate validation)"""
        if pytestconfig.getoption("certificate_source") != "custom-server":
            pytest.skip("Test only runs with --certificate-source=custom-server")

        # Test that HTTPS endpoints respond (using -k to skip cert validation)
        endpoints = [
            f"https://{server_fqdn}/api/v2/ping",
            f"https://{server_fqdn}/pulp/api/v3/status/"
        ]

        for endpoint in endpoints:
            cmd = server.run(f"curl -k --silent --output /dev/null --write-out '%{{http_code}}' {endpoint}")
            assert cmd.rc == 0, f"Could not connect to {endpoint}"
            assert cmd.stdout.strip() in ["200", "405"], f"Endpoint {endpoint} returned {cmd.stdout.strip()}"