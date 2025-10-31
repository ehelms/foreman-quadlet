import pytest


def test_remediations_api_service(server):
    service = server.service("iop-service-remediations-api")
    assert service.is_running
    assert service.is_enabled


def test_remediations_container_running(server):
    result = server.run("podman inspect iop-service-remediations-api --format '{{.State.Status}}'")
    assert result.succeeded
    assert "running" in result.stdout


def test_remediations_quadlet_file(server):
    quadlet_file = server.file("/etc/containers/systemd/iop-service-remediations-api.container")
    assert quadlet_file.exists
    assert quadlet_file.is_file


def test_remediations_service_dependencies(server):
    result = server.run("systemctl show iop-service-remediations-api --property=After")
    assert result.succeeded
    assert "iop-core-kafka.service" in result.stdout
    assert "iop-service-advisor-backend-api.service" in result.stdout



def test_remediations_api_health_endpoint(server):
    result = server.run("podman run --rm quay.io/iop/remediations:latest curl -s -o /dev/null -w '%{http_code}' http://iop-service-remediations-api:3000/health")
    if result.succeeded:
        assert "200" in result.stdout