# IOP Design

## Architecture Overview
- **Container-based Services**: Podman containers managed as systemd services
- **Event-Driven Messaging**: Kafka message bus for real-time data processing
- **Data Processing Pipeline**: Ingress → Collection (Puptoo/Yuptoo) → Engine → Gateway
- **Insights & Analytics**: Optional advisor and remediation services for system optimization
- **Frontend Integration**: Web interfaces for recommendations and remediation management
- **Host Integration**: Network host mode for simplified communication
- **Service Dependencies**: Automated startup ordering through systemd

## Container Types Overview

The IOP deployment uses containerized services managed by systemd:

- **Persistent Service**: Long-running containers that provide continuous functionality as systemd services
- **Static Assets**: Frontend web assets extracted from containers and served by Apache
- **Service Dependencies**: Services have defined startup order and dependencies
- **Configuration Secrets**: Service-specific configuration managed through Podman secrets

## Core Infrastructure Services

### Message Bus and Event Processing
- **`iop-core-kafka`** *[Persistent Service]*: Apache Kafka message broker
  - Purpose: Central message bus for inter-service communication
  - Dependencies: None (starts first)

### Gateway Services
- **`iop-core-gateway`** *[Persistent Service]*: Gateway service for external communication
  - Purpose: Handles external requests and routes to internal services
  - Dependencies: Kafka, Engine, Ingress services

### Core Processing Services
- **`iop-core-engine`** *[Persistent Service]*: Central insights processing engine
  - Purpose: Main processing engine that orchestrates data analysis
  - Dependencies: Kafka and Ingress services

- **`iop-core-ingress`** *[Persistent Service]*: Data ingress service
  - Purpose: Handles incoming data uploads and validation
  - Dependencies: Kafka service

### Data Collection Services
- **`iop-core-puptoo`** *[Persistent Service]*: System data collection and transformation
  - Purpose: Processes system information from uploads
  - Dependencies: Kafka service

- **`iop-core-yuptoo`** *[Persistent Service]*: YUM/DNF package data collection
  - Purpose: Processes package information and repositories
  - Dependencies: Kafka service

## Optional Services

### Advisor Services
- **`iop-service-advisor-backend-api`** *[Persistent Service]*: Advisor API service
  - Purpose: Provides advisor recommendations API for system optimization
  - Port: 8000 (internal)
  - Environment: Production configuration with Django backend
  - Dependencies: Kafka service
  - Image: `quay.io/iop/advisor-backend:latest`

- **`iop-service-advisor-backend-service`** *[Persistent Service]*: Advisor processing service
  - Purpose: Processes advisor data and generates system recommendations
  - Command: `pipenv run python service/service.py`
  - Dependencies: Kafka service
  - Image: `quay.io/iop/advisor-backend:latest`

### Remediation Services
- **`iop-service-remediations-api`** *[Persistent Service]*: Remediations API service
  - Purpose: Provides automated remediation suggestions and playbooks
  - Command: Node.js API server with database migrations
  - Integration: Connects to Advisor API for recommendation data
  - Dependencies: Kafka service, Advisor Backend API service
  - Image: `quay.io/iop/remediations:latest`

### Frontend Assets

- **Advisor Frontend** *[Static Assets]*: Frontend UI for advisor recommendations
  - Purpose: Web interface for viewing system optimization recommendations
  - Location: `/var/lib/foreman/public/assets/apps/advisor`
  - Source: Extracted from `quay.io/iop/advisor-frontend` container
  - Owner: foreman:foreman
  - Access: Served via Foreman's Apache/Nginx

- **Remediations Frontend** *[Static Assets]*: Frontend UI for remediations
  - Purpose: Web interface for managing automated remediation suggestions
  - Location: `/var/lib/foreman/public/assets/apps/remediations`
  - Source: Extracted from `quay.io/iop/remediations-frontend` container
  - Owner: foreman:foreman
  - Access: Served via Foreman's Apache/Nginx

## Service Dependencies

### Startup Order
1. **Message Bus**: `iop-core-kafka`
2. **Data Services**: `iop-core-ingress`, `iop-core-puptoo`, `iop-core-yuptoo`
3. **Processing**: `iop-core-engine`
4. **Gateway**: `iop-core-gateway`
5. **Optional Services**: `iop-service-advisor-backend-api`, `iop-service-advisor-backend-service`
6. **Dependent Services**: `iop-service-remediations-api` (depends on advisor services)
7. **Frontend Assets**: Advisor and Remediations frontends (static asset extraction)

### Inter-Service Communication
- **Host Networking**: All services use host network mode for simplified communication
- **Kafka Topics**: Event-driven messaging between services
- **Service Dependencies**: Systemd Wants/After directives ensure proper startup order

## Container Orchestration
- **Podman Quadlet**: Systemd-native container management
- **Service dependencies**: Automated ordering through systemd units
- **Host Networking**: Services communicate via localhost
- **Container images**: Configurable container images and tags per service

## Configuration Management
- **Podman Secrets**: Service-specific configuration secrets (engine config, Kafka properties)
- **Template-based Config**: Configuration files generated from Ansible templates
- **Environment Variables**: Runtime configuration through container environment
- **Host Networking**: All services use host network mode with localhost communication
- **Service Discovery**: Services communicate via well-known localhost ports

## Service Endpoints and Integration

### Core Service Endpoints
- **Kafka**: `localhost:9092` - Message broker for inter-service communication
- **Ingress**: `localhost:8080` - Data ingress and validation endpoint
- **Gateway**: `localhost:24443` - External gateway for smart proxy integration

### Optional Service Endpoints
- **Advisor API**: `localhost:8000` - Advisor recommendations API
- **Host Inventory**: `localhost:8081` - Host inventory data API (when available)

### Service Integration Points
- **Advisor ↔ Kafka**: Real-time recommendation processing via message queues
- **Remediations ↔ Advisor**: Automated fix suggestions based on advisor recommendations
- **Remediations ↔ Inventory**: Host data integration for targeted remediation
- **Frontend ↔ APIs**: Web interfaces consume backend APIs for user interaction

### Configuration Endpoints
Services are configured to communicate via localhost endpoints:
- `BOOTSTRAP_SERVERS=localhost:9092` (Kafka connection)
- `ADVISOR_HOST=http://localhost:8000` (Advisor API)
- `INVENTORY_HOST=http://localhost:8081` (Inventory API)

## Service Management
All IOP services can be managed through standard systemd commands:

```bash
# Check service status
systemctl status iop-core-*
systemctl status iop-service-*

# Start/stop individual services
systemctl start iop-core-kafka
systemctl stop iop-core-engine
systemctl start iop-service-advisor-backend-api
systemctl start iop-service-remediations-api

# View service logs
journalctl -u iop-core-kafka -f
journalctl -u iop-service-advisor-backend-api -f
journalctl -u iop-service-remediations-api -f

# Check container status
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Monitor all IOP services
watch 'systemctl status iop-core-* iop-service-*'
```

## Deployment Architecture

### Core Services Deployment
Core IOP services are always deployed when `--enable-iop` is used:
1. Kafka message bus (foundational service)
2. Data ingestion and processing services (ingress, puptoo, yuptoo)
3. Processing engine and gateway services

### Optional Services Deployment
Advisor and remediation services are deployed as part of the core IOP package:
1. Advisor backend services (API and processing)
2. Remediations API service
3. Frontend asset extraction

### Role Structure
```
src/roles/
├── iop_core/              # Main IOP orchestration role
├── iop_kafka/             # Kafka message broker
├── iop_ingress/           # Data ingress service
├── iop_gateway/           # External gateway
├── iop_engine/            # Processing engine
├── iop_puptoo/            # System data collection
├── iop_yuptoo/            # Package data collection
├── iop_advisor/           # Advisor backend services
├── iop_advisor_frontend/  # Advisor UI assets
├── iop_remediations/      # Remediations API
├── iop_vulnerability/     # Vulnerability analysis engine
├── iop_vulnerability_frontend/ # Vulnerability UI assets
└── iop_vmaas/             # VMAAS vulnerability database services
```

## Handler Integration
Each IOP service includes restart handlers that:
- Check if the service exists before attempting operations
- Only restart services that are actually deployed
- Provide safe restart capabilities during configuration updates

The handlers follow a consistent pattern:
1. Check service status to verify existence
2. Restart service only if it's loaded and available
3. Use proper service naming conventions with role prefixes

## Testing

The IOP implementation includes comprehensive test suites for all services:

### Test Coverage
- **Service Health**: Verify services are running and enabled
- **Container Status**: Check container runtime status
- **Configuration**: Validate service configuration and dependencies
- **Connectivity**: Test inter-service communication
- **Frontend Assets**: Verify static asset extraction and deployment

### Test Files
- `tests/iop/test_advisor.py`: Tests for advisor backend services and frontend assets
- `tests/iop/test_remediations.py`: Tests for remediations API service and frontend assets
- `tests/iop/test_engine.py`: Tests for engine service
- `tests/iop/test_kafka.py`: Tests for Kafka message bus
- `tests/iop/test_gateway.py`: Tests for gateway service
- `tests/iop/test_ingress.py`: Tests for ingress service
- `tests/iop/test_puptoo.py`: Tests for puptoo data collection
- `tests/iop/test_yuptoo.py`: Tests for yuptoo package data collection
- `tests/iop/test_integration.py`: Integration tests across services

## Troubleshooting

### Common Issues

#### Service Startup Problems
```bash
# Check service dependencies
systemctl list-dependencies iop-service-advisor-backend-api

# Verify Kafka is running before dependent services
systemctl status iop-core-kafka

# Check for failed services
systemctl --failed | grep iop
```

#### Container Issues
```bash
# Check container logs for errors
podman logs iop-service-advisor-backend-api

# Verify container health
podman inspect iop-service-advisor-backend-api --format '{{.State.Status}}'

# Check resource usage
podman stats
```

#### Frontend Asset Problems
```bash
# Verify assets were extracted
ls -la /var/lib/foreman/public/assets/apps/advisor/
ls -la /var/lib/foreman/public/assets/apps/remediations/

# Check file ownership
ls -la /var/lib/foreman/public/assets/apps/
```

#### Network Connectivity
```bash
# Test Kafka connectivity
podman exec iop-core-kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# Test advisor API
curl -s http://localhost:8000/health || echo "Advisor API not responding"

# Check port usage
ss -tulpn | grep -E ':(8000|8080|8081|9092)'
```

### Log Locations
- **Service Logs**: `journalctl -u <service-name>`
- **Container Logs**: `podman logs <container-name>`
- **Quadlet Files**: `/etc/containers/systemd/`
- **Secrets**: `podman secret ls`

### Performance Monitoring
```bash
# Monitor service resource usage
systemctl status iop-service-advisor-backend-api
podman stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check Kafka topics and messages
podman exec iop-core-kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --from-beginning --max-messages 5 \
  --topic advisor.recommendations
```