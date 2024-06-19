import logging
from datetime import datetime, timezone
from os import environ
from pathlib import Path
from sys import stdout

import dotenv
import httpx
from discord_webhook import DiscordEmbed, DiscordWebhook
from httpx import ReadTimeout, Response, TimeoutException
from loguru import logger
from loguru_discord import DiscordSink

from handlers.intercept import Intercept


def Start() -> None:
    """Initialize Leash and begin primary functionality."""

    logger.info("Leash")
    logger.info("https://github.com/EthanC/Leash")

    if dotenv.load_dotenv():
        logger.success("Loaded environment variables")

    if level := environ.get("LOG_LEVEL"):
        logger.remove()
        logger.add(stdout, level=level)

        logger.success(f"Set console logging level to {level}")

    if url := environ.get("LOG_DISCORD_WEBHOOK_URL"):
        logger.add(
            DiscordSink(url, suppress=[ReadTimeout, TimeoutException]),
            level=environ.get("LOG_DISCORD_WEBHOOK_LEVEL", "WARNING"),
            backtrace=False,
        )

        logger.success(f"Enabled logging to Discord webhook")

    # Reroute standard logging to Loguru
    logging.basicConfig(handlers=[Intercept()], level=0, force=True)

    latest: int = Checkpoint()
    leases: list[dict[str, str]] = GetLeasesDHCPv4()

    CheckLeases(leases, latest)

    Checkpoint(int(datetime.now(timezone.utc).timestamp()))


def Checkpoint(new: int | None = None) -> int:
    """
    Return the latest checkpoint, and save the optionally provided
    checkpoint to the local disk.
    """

    value: int = int(datetime.now(timezone.utc).timestamp())
    humanized: str | None = None

    if new:
        value = new
        humanized = datetime.fromtimestamp(value, timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        with open("checkpoint.txt", "w+") as file:
            file.write(str(value))

        logger.info(f"Saved checkpoint at {humanized} ({value})")
    elif Path("checkpoint.txt").is_file():
        with open("checkpoint.txt", "r") as file:
            value = int(file.read())

        humanized = datetime.fromtimestamp(value, timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        logger.info(f"Loaded checkpoint at {humanized} ({value})")
    else:
        humanized = datetime.fromtimestamp(value, timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        logger.info(
            f"Checkpoint not found, defaulted to current time {humanized} ({value})"
        )

    return value


def GetLeasesDHCPv4() -> list[dict[str, str]]:
    """
    Fetch a list of DHCPv4 leases from the configured
    OPNsense instance.
    """

    opnUrl: str | None = environ.get("OPNSENSE_ADDRESS")
    opnKey: str | None = environ.get("OPNSENSE_KEY")
    opnSecret: str | None = environ.get("OPNSENSE_SECRET")

    leases: list[dict[str, str]] = []

    if not opnUrl:
        logger.error("OPNsense address is not set")

        return leases

    if (not opnKey) or (not opnSecret):
        logger.error("OPNsense credentials are not set")

        return leases

    try:
        res: Response = httpx.post(
            f"{opnUrl}/api/dhcpv4/leases/searchLease",
            json={"inactive": True},
            auth=(opnKey, opnSecret),
            verify=False,
        )

        logger.trace(res.text)

        res.raise_for_status()

        leases = res.json()["rows"]
    except ReadTimeout as e:
        # Suppress ReadTimeout exceptions due to frequency
        logger.opt(exception=e).info("Failed to fetch DHCPv4 Leases from OPNsense")
    except Exception as e:
        logger.opt(exception=e).error("Failed to fetch DHCPv4 Leases from OPNsense")

    logger.info(f"Fetched {len(leases):,} DHCPv4 Leases from OPNsense")

    return leases


def CheckLeases(leases: list[dict[str, str]], checkpoint: int) -> None:
    """Process the provided list for newly-detected DHCPv4 leases."""

    for lease in leases:
        logger.trace(lease)

        # Prefer to use hostname but fallback to address
        name: str = lease.get("hostname") or lease.get("address", "Unknown")
        starts: int | str | None = None

        if not (starts := lease.get("starts")):
            logger.debug(f"Skipping Lease {name} due to lack of a starts value")

            continue

        starts = int(datetime.strptime(starts, "%Y/%m/%d %H:%M:%S").timestamp())

        if starts > checkpoint:
            logger.success(
                f"Detected new OPNsense DHCPv4 Lease {name} ({starts} > {checkpoint})"
            )

            Notify(lease)

    logger.info(f"Processed {len(leases):,} DHCPv4 Leases from OPNsense")


def Notify(lease: dict[str, str]) -> None:
    """Report newly-detected DHCPv4 Leases to the configured Discord webhook."""

    if not (url := environ.get("DISCORD_WEBHOOK_URL")):
        logger.info(f"Discord webhook for notifications is not set")

        return

    embed: DiscordEmbed = DiscordEmbed("New DHCPv4 Lease", color="D94F00")

    embed.set_author(
        "OPNsense",
        url=environ.get("OPNSENSE_ADDRESS", "https://opnsense.org/"),
        icon_url="https://i.imgur.com/0YtoNjj.png",
    )

    if type := lease.get("type"):
        embed.add_embed_field("Type", f"{type.title()}")

    if starts := lease.get("starts"):
        starts = int(datetime.strptime(starts, "%Y/%m/%d %H:%M:%S").timestamp())

        embed.add_embed_field("Issued", f"<t:{starts}:R>")

    if ends := lease.get("ends"):
        ends = int(datetime.strptime(ends, "%Y/%m/%d %H:%M:%S").timestamp())

        embed.add_embed_field("Expiration", f"<t:{ends}:R>")

    if interface := lease.get("if_descr"):
        embed.add_embed_field("Interface", interface)

    if mac := lease.get("mac"):
        embed.add_embed_field("MAC Address", f"`{mac.upper()}`")

    if ip := lease.get("address"):
        embed.add_embed_field("IPv4 Address", f"`{ip}`")

    if manufacturer := lease.get("man"):
        embed.add_embed_field("Manufacturer", manufacturer, inline=False)

    if hostname := lease.get("hostname"):
        embed.add_embed_field("Hostname", hostname, inline=False)

    if description := lease.get("descr"):
        embed.add_embed_field("Description", description, inline=False)

    embed.set_footer("Leash", icon_url="https://i.imgur.com/2TwoCuY.png")  # type: ignore
    embed.set_timestamp(datetime.now(timezone.utc))

    DiscordWebhook(url=url, embeds=[embed], rate_limit_retry=True).execute()


try:
    Start()
except Exception as e:
    logger.opt(exception=e).critical("Fatal error occurred during runtime")
