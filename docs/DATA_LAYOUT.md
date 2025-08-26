# Data Layout

## Boot Configuration

Paths to external services are stored in `config/boot_paths.yml` relative to the project base directory. Each entry maps a service name to the absolute path of its executable. Adjust this file if binaries such as OBS or the MediaMTX server are installed in non-default locations.

## Networking

Cyclone's RTSP streams default to port **8554**. MediaMTX and health checks assume this port unless overridden.

## Common Failure Modes

- Missing executable or incorrect entry in `config/boot_paths.yml` prevents a service from starting.
- `config/boot_paths.yml` absent or unreadable.
- Local firewall blocking TCP traffic on port **8554**, preventing RTSP streams from connecting.
