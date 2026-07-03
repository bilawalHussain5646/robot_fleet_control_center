# Architecture

React communicates with FastAPI through `/api/v1` and `/ws/fleet`. PostgreSQL stores users, robots, commands, telemetry, tasks, alerts, maintenance, refresh tokens, and audit logs. Redis is included for future broadcast/rate-limit coordination; the development app degrades without relying on it for core behavior.

The simulator runs as a background task and all robot-facing code should go through the RobotAdapter abstraction.
