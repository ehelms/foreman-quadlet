import pytest


def test_advisor_backend_api_service(server):
    service = server.service("iop-service-advisor-backend-api")
    assert service.is_running
    assert service.is_enabled


def test_advisor_backend_service_service(server):
    service = server.service("iop-service-advisor-backend-service")
    assert service.is_running
    assert service.is_enabled


def test_advisor_frontend_directory(server):
    frontend_dir = server.file("/var/lib/foreman/public/assets/apps/advisor")
    assert frontend_dir.exists
    assert frontend_dir.is_directory
    assert frontend_dir.mode == 0o755


def test_advisor_frontend_app_info(server):
    app_info = server.file("/var/lib/foreman/public/assets/apps/advisor/app.info.json")
    assert app_info.exists
    assert app_info.is_file