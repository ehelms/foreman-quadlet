import pytest


def test_remediation_api_service(server):
    service = server.service("iop-service-remediations-api")
    assert service.is_running
    assert service.is_enabled