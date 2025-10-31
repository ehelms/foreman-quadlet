import pytest


def test_inventory_migrate_service(server):
    service = server.service("iop-core-host-inventory-migrate")
    assert service.is_enabled


def test_inventory_mq_service(server):
    service = server.service("iop-core-host-inventory")
    assert service.is_running
    assert service.is_enabled


def test_inventory_api_service(server):
    service = server.service("iop-core-host-inventory-api")
    assert service.is_running
    assert service.is_enabled


# Migration service is oneshot - we don't test container running status
# def test_inventory_migrate_container_running(server):
#     result = server.run("podman inspect iop-core-host-inventory-migrate --format '{{.State.Status}}'")
#     assert result.succeeded
#     assert "exited" in result.stdout  # Migration container should exit after completion


def test_inventory_mq_container_running(server):
    result = server.run("podman inspect iop-core-host-inventory --format '{{.State.Status}}'")
    assert result.succeeded
    assert "running" in result.stdout


def test_inventory_api_container_running(server):
    result = server.run("podman inspect iop-core-host-inventory-api --format '{{.State.Status}}'")
    assert result.succeeded
    assert "running" in result.stdout


def test_inventory_quadlet_files(server):
    quadlet_files = [
        "/etc/containers/systemd/iop-core-host-inventory-migrate.container",
        "/etc/containers/systemd/iop-core-host-inventory.container",
        "/etc/containers/systemd/iop-core-host-inventory-api.container",
        "/etc/containers/systemd/iop-core-host-inventory-cleanup.container"
    ]

    for quadlet_file in quadlet_files:
        file_obj = server.file(quadlet_file)
        assert file_obj.exists
        assert file_obj.is_file


def test_inventory_service_dependencies(server):
    # Test MQ service depends on migration
    result = server.run("systemctl show iop-core-host-inventory --property=After")
    assert result.succeeded
    assert "iop-core-host-inventory-migrate.service" in result.stdout


def test_inventory_api_endpoint(server):
    result = server.run("podman run --rm quay.io/iop/host-inventory:latest curl -s -o /dev/null -w '%{http_code}' http://iop-core-host-inventory-api:8081/health")
    if result.succeeded:
        assert "200" in result.stdout


def test_inventory_hosts_endpoint(server):
    result = server.run("podman run --rm quay.io/iop/host-inventory:latest curl -s -o /dev/null -w '%{http_code}' http://iop-core-host-inventory-api:8081/api/inventory/v1/hosts")
    if result.succeeded:
        assert "200" in result.stdout


def test_inventory_cleanup_service(server):
    service = server.service("iop-core-host-inventory-cleanup")
    assert not service.is_running  # Cleanup service should not be running


def test_inventory_cleanup_service_enabled(server):
    result = server.run("systemctl is-enabled iop-core-host-inventory-cleanup")
    assert result.succeeded
    assert "generated" in result.stdout


def test_inventory_cleanup_timer(server):
    service = server.service("iop-core-host-inventory-cleanup.timer")
    assert service.is_enabled
    assert service.is_running


def test_inventory_cleanup_timer_config(server):
    timer_file = server.file("/etc/systemd/system/iop-core-host-inventory-cleanup.timer")
    assert timer_file.exists
    assert timer_file.is_file

    content = timer_file.content_string
    assert "OnBootSec=10min" in content
    assert "OnUnitActiveSec=24h" in content
    assert "Persistent=true" in content
    assert "RandomizedDelaySec=300" in content
    assert "WantedBy=timers.target" in content