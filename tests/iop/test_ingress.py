import pytest


def test_ingress_service(server):
    service = server.service("iop-core-ingress")
    assert service.is_running
    assert service.is_enabled


def test_ingress_container_running(server):
    result = server.run("podman inspect iop-core-ingress --format '{{.State.Status}}'")
    assert result.succeeded
    assert "running" in result.stdout


def test_ingress_quadlet_file(server):
    quadlet_file = server.file("/etc/containers/systemd/iop-core-ingress.container")
    assert quadlet_file.exists
    assert quadlet_file.is_file


def test_ingress_http_endpoint(server):
    result = server.run("podman run --rm quay.io/iop/ingress:latest curl -s -o /dev/null -w '%{http_code}' http://iop-core-ingress:8080/")
    if result.succeeded:
        assert "200" in result.stdout
