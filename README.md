# Leash

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/EthanC/Leash/ci.yaml?branch=main) ![Docker Pulls](https://img.shields.io/docker/pulls/ethanchrisp/leash?label=Docker%20Pulls) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/ethanchrisp/leash/latest?label=Docker%20Image%20Size)

Leash monitors the OPNsense DHCPv4 service and notifies about new leases via Discord.

<p align="center">
    <img src="https://i.imgur.com/iYiKFBS.png" draggable="false">
</p>

## Setup

Although not required, a [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) is recommended for notifications.

Regardless of your chosen setup method, Leash is intended for use with a task scheduler, such as [cron](https://crontab.guru/).

**Environment Variables:**

-   `LOG_LEVEL`: [Loguru](https://loguru.readthedocs.io/en/stable/api/logger.html) severity level to write to the console.
-   `LOG_DISCORD_WEBHOOK_URL`: [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) URL to receive log events.
-   `LOG_DISCORD_WEBHOOK_LEVEL`: Minimum [Loguru](https://loguru.readthedocs.io/en/stable/api/logger.html) severity level to forward to Discord.
-   `OPNSENSE_ADDRESS` (Required): IP or URL for the local OPNsense instance.
-   `OPNSENSE_KEY` (Required): Key for the local OPNsense instance.
-   `OPNSENSE_SECRET` (Required): Secret for the local OPNsense instance.
-   `DISCORD_WEBHOOK_URL`: [Discord Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) URL to receive OPNsense DHCPv4 Lease notifications.

### Docker (Recommended)

Modify the following `compose.yaml` example file, then run `docker compose up`.

```yml
services:
  leash:
    container_name: leash
    image: ethanchrisp/leash:latest
    environment:
      LOG_LEVEL: INFO
      LOG_DISCORD_WEBHOOK_URL: https://discord.com/api/webhooks/YYYYYYYY/YYYYYYYY
      LOG_DISCORD_WEBHOOK_LEVEL: WARNING
      OPNSENSE_ADDRESS: https://192.168.1.1
      OPNSENSE_KEY: XXXXXXXX
      OPNSENSE_SECRET: XXXXXXXX
      DISCORD_WEBHOOK_URL: https://discord.com/api/webhooks/XXXXXXXX/XXXXXXXX
```

### Standalone

Leash is built for [Python 3.12](https://www.python.org/) or greater.

1. Install required dependencies using [uv](https://github.com/astral-sh/uv): `uv sync`
2. Rename `.env.example` to `.env`, then provide the environment variables.
3. Start Leash: `python leash.py`
