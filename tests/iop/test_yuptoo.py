import pytest


def test_yuptoo_service(server):
    service = server.service("iop-core-yuptoo")
    assert service.is_running
    assert service.is_enabled


def test_yuptoo_service_dependencies(server):
    result = server.run("systemctl show iop-core-yuptoo --property=After")
    assert result.succeeded
    assert "iop-core-kafka.service" in result.stdout


def test_yuptoo_http_endpoint(server):
    result = server.run("podman run --rm quay.io/iop/yuptoo:latest curl -s -o /dev/null -w '%{http_code}' http://iop-core-yuptoo:5005/")
    if result.succeeded:
        assert "200" in result.stdout
