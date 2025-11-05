import pytest


def test_puptoo_service(server):
    service = server.service("iop-core-puptoo")
    assert service.is_running
    assert service.is_enabled


def test_puptoo_http_endpoint(server):
    result = server.run("curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/metrics")
    assert result.succeeded
    assert "200" in result.stdout