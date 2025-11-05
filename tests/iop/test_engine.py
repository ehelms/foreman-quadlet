import pytest


def test_engine_service(server):
    service = server.service("iop-core-engine")
    assert service.is_running
    assert service.is_enabled


def test_engine_secret(server):
    result = server.run("podman secret ls --format '{{.Name}}'")
    assert result.succeeded
    assert "iop-core-engine-config-yml" in result.stdout