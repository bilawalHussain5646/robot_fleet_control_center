# AI Powered Robot Fleet Control Center

A production-style Robot Fleet Management and Monitoring Platform with a React dashboard, FastAPI backend, PostgreSQL, Redis, live WebSocket robot telemetry, command APIs, task management, alerts, maintenance, analytics, camera simulation, audit logs, and a mock AI fleet assistant.

## Features

- JWT authentication with Admin, Operator, Technician, and Viewer roles.
- Seeded local users, 10 simulated robots, tasks, alerts, maintenance records, and audit logs.
- Live robot telemetry over `/ws/fleet` with automatic frontend reconnection.
- Indoor SVG warehouse map with live robot markers, headings, zones, charging stations, restricted area, and maintenance bay.
- Robot commands: start, stop, pause, resume, move to coordinate, speed control, charger, restart, emergency stop, and clear emergency stop.
- Alerts, maintenance tickets, task creation and automatic robot assignment.
- Mock MJPEG-style camera stream per robot.
- Mock AI assistant using predefined safe fleet tools and audit logging.
- Docker Compose with frontend, backend, PostgreSQL, Redis, and Nginx.

## Quick Start

```bash
docker compose up --build
```

Frontend: http://localhost:5173
Backend API: http://localhost:8000/api/v1/health
OpenAPI docs: http://localhost:8000/docs
Nginx entrypoint: http://localhost:8080

## Local Development Users

These credentials are for local development only.

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@example.com | Admin123! |
| Operator | operator@example.com | Operator123! |
| Technician | technician@example.com | Technician123! |
| Viewer | viewer@example.com | Viewer123! |

## Architecture

The backend exposes versioned `/api/v1` REST endpoints and `/ws/fleet` WebSocket events. The simulator runs as a FastAPI background task and updates robots every 1-2 seconds without blocking the server. SQLAlchemy models isolate persistence, and the `RobotAdapter` abstraction allows later MQTT, REST, WebSocket, or ROS 2 bridges.

## Environment

Copy `.env.example` to `.env` for local overrides. Never commit real secrets. Important variables include `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `SIMULATION_ENABLED`, `SIMULATION_ROBOT_COUNT`, `SIMULATION_UPDATE_INTERVAL`, `TELEMETRY_STORAGE_INTERVAL`, `OPENAI_API_KEY`, `AI_MODEL`, and `CORS_ORIGINS`.

## Tests

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

## WebSocket Events

The simulator broadcasts events such as `robot.telemetry`, `robot.command_updated`, and `fleet.summary_updated`. Telemetry messages include battery, temperature, speed, location, heading, CPU, memory, and status.

## Real Robot Integration

Real robots should be connected by implementing the `RobotAdapter` interface: `connect`, `disconnect`, `get_status`, `get_telemetry`, `send_command`, `assign_task`, `get_camera_source`, and `health_check`. Placeholder adapter classes are included for MQTT, REST, and ROS 2.

## Production Notes

Use a strong `JWT_SECRET`, external PostgreSQL/Redis, HTTPS termination, restricted CORS, secret management, backup policies, and observability. The default accounts and `.env.example` values are not production secrets.
