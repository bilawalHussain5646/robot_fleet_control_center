# WebSocket Events

Endpoint: `/ws/fleet`.

Events include `robot.telemetry`, `robot.command_updated`, `fleet.summary_updated`, and are shaped as `{ event, timestamp, robot_id, data }` when robot-specific.
