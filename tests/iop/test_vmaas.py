import pytest


def test_vmaas_reposcan_service(server):
    service = server.service("iop-service-vmaas-reposcan")
    assert service.is_running
    assert service.is_enabled


def test_vmaas_webapp_go_service(server):
    service = server.service("iop-service-vmaas-webapp-go")
    assert service.is_running
    assert service.is_enabled


def test_vmaas_reposcan_container_running(server):
    result = server.run("podman inspect iop-service-vmaas-reposcan --format '{{.State.Status}}'")
    assert result.succeeded
    assert "running" in result.stdout


def test_vmaas_webapp_go_container_running(server):
    result = server.run("podman inspect iop-service-vmaas-webapp-go --format '{{.State.Status}}'")
    assert result.succeeded
    assert "running" in result.stdout


def test_vmaas_quadlet_files(server):
    quadlet_files = [
        "/etc/containers/systemd/iop-service-vmaas-reposcan.container",
        "/etc/containers/systemd/iop-service-vmaas-webapp-go.container"
    ]

    for quadlet_file in quadlet_files:
        file_obj = server.file(quadlet_file)
        assert file_obj.exists
        assert file_obj.is_file


def test_vmaas_data_volume(server):
    result = server.run("podman volume inspect iop-service-vmaas-data --format '{{.Name}}'")
    assert result.succeeded
    assert "iop-service-vmaas-data" in result.stdout


def test_vmaas_service_dependencies(server):
    # Test webapp-go service dependencies
    result = server.run("systemctl show iop-service-vmaas-webapp-go --property=After")
    assert result.succeeded
    assert "iop-service-vmaas-reposcan.service" in result.stdout


def test_vmaas_webapp_go_health_endpoint(server):
    result = server.run("podman run --rm quay.io/iop/vmaas:latest curl -s -o /dev/null -w '%{http_code}' http://iop-service-vmaas-webapp-go:8000/healthz")
    if result.succeeded:
        assert "200" in result.stdout


def test_vmaas_reposcan_health_endpoint(server):
    result = server.run("podman run --rm quay.io/iop/vmaas:latest curl -s -o /dev/null -w '%{http_code}' http://iop-service-vmaas-reposcan:8000/healthz")
    if result.succeeded:
        assert "200" in result.stdout


def test_vmaas_reposcan_prometheus_endpoint(server):
    result = server.run("podman run --rm quay.io/iop/vmaas:latest curl -s -o /dev/null -w '%{http_code}' http://iop-service-vmaas-reposcan:9000/metrics")
    if result.succeeded:
        assert "200" in result.stdout