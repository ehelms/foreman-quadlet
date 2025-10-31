import pytest


def test_advisor_backend_api_service(server):
    service = server.service("iop-service-advisor-backend-api")
    assert service.is_running
    assert service.is_enabled


def test_advisor_backend_service(server):
    service = server.service("iop-service-advisor-backend-service")
    assert service.is_running
    assert service.is_enabled


def test_advisor_backend_api_container_running(server):
    result = server.run("podman inspect iop-service-advisor-backend-api --format '{{.State.Status}}'")
    assert result.succeeded
    assert "running" in result.stdout


def test_advisor_backend_service_container_running(server):
    result = server.run("podman inspect iop-service-advisor-backend-service --format '{{.State.Status}}'")
    assert result.succeeded
    assert "running" in result.stdout


def test_advisor_quadlet_files(server):
    api_quadlet = server.file("/etc/containers/systemd/iop-service-advisor-backend-api.container")
    assert api_quadlet.exists
    assert api_quadlet.is_file

    service_quadlet = server.file("/etc/containers/systemd/iop-service-advisor-backend-service.container")
    assert service_quadlet.exists
    assert service_quadlet.is_file


def test_advisor_service_dependencies(server):
    result = server.run("systemctl show iop-service-advisor-backend-api --property=After")
    assert result.succeeded
    assert "iop-core-kafka.service" in result.stdout


def test_advisor_kafka_connectivity(server):
    result = server.run("podman logs iop-service-advisor-backend-api 2>&1 | grep -i 'kafka\\|bootstrap'")
    assert result.succeeded


def test_advisor_frontend_assets(server):
    assets_dir = server.file("/var/lib/foreman/public/assets/apps/advisor")
    assert assets_dir.exists
    assert assets_dir.is_directory
    assert assets_dir.mode == 0o755

    app_info_file = server.file("/var/lib/foreman/public/assets/apps/advisor/app.info.json")
    assert app_info_file.exists
    assert app_info_file.is_file


def test_advisor_api_health_endpoint(server):
    result = server.run("podman run --rm quay.io/iop/advisor-backend:latest curl -s -o /dev/null -w '%{http_code}' http://iop-service-advisor-backend-api:8000/api/insights/v1/status/live/")
    if result.succeeded:
        assert "200" in result.stdout


def test_advisor_fdw_foreign_server(server):
    result = server.run('podman exec -e PGPASSWORD=CHANGEME postgresql psql advisor_db -U postgres -c "SELECT * FROM pg_foreign_server WHERE srvname = \'hbi_server\';"')
    assert result.succeeded
    assert "hbi_server" in result.stdout


def test_advisor_fdw_user_mappings(server):
    result = server.run('podman exec -e PGPASSWORD=CHANGEME postgresql psql advisor_db -U postgres -c "SELECT * FROM information_schema.user_mappings WHERE foreign_server_name = \'hbi_server\';"')
    assert result.succeeded
    assert "advisor_user" in result.stdout


def test_advisor_fdw_foreign_tables(server):
    result = server.run('podman exec -e PGPASSWORD=CHANGEME postgresql psql advisor_db -U postgres -c "\\det inventory_source.*"')
    assert result.succeeded
    assert "hosts" in result.stdout


def test_advisor_fdw_views(server):
    result = server.run('podman exec -e PGPASSWORD=CHANGEME postgresql psql advisor_db -U postgres -c "\\dv inventory.*"')
    assert result.succeeded
    assert "hosts" in result.stdout


def test_advisor_fdw_foreign_table_query(server):
    result = server.run('podman exec -e PGPASSWORD=CHANGEME postgresql psql advisor_db -c "SELECT COUNT(*) FROM inventory_source.hosts;"')
    assert result.succeeded

def test_advisor_fdw_view_query(server):
    result = server.run('podman exec -e PGPASSWORD=CHANGEME postgresql psql advisor_db -c "SELECT COUNT(*) FROM inventory.hosts;"')
    assert result.succeeded

def test_advisor_fdw_postgres_user_access(server):
    result = server.run('podman exec -e PGPASSWORD=CHANGEME postgresql psql advisor_db -U postgres -c "SELECT COUNT(*) FROM inventory.hosts;"')
    assert result.succeeded