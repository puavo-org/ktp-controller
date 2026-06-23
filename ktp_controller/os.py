# Standard library imports
import logging
import time
import typing

# Third-party imports
import psutil

# Internal imports
import ktp_controller.utils

_LOGGER = logging.getLogger(__name__)


def get_uptime() -> float:
    # Uptime is current time minus boot time
    return float(time.time() - psutil.boot_time())


def get_disk_usage_stats() -> list[dict[str, typing.Any]]:
    stats: list[dict[str, typing.Any]] = []

    # all=False returns only physical disk partitions, ignoring pseudo-filesystems
    partitions = psutil.disk_partitions(all=False)

    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            stats.append(
                {
                    "mountpoint": partition.mountpoint,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                }
            )
        except PermissionError:
            # Some physical partitions (like certain restricted mounts) might deny access
            continue
        except FileNotFoundError:
            # Safely ignore if the mount point disappears during iteration
            continue

    return stats


def get_load_average_stats() -> dict[str, typing.Any]:
    load1, load5, load15 = psutil.getloadavg()
    return {
        "1min": load1,
        "5min": load5,
        "15min": load15,
    }


def get_memory_stats() -> dict[str, typing.Any]:
    mem = psutil.virtual_memory()
    return {
        "total": mem.total,
        "used": mem.used,
        "free": mem.free,
        "available": mem.available,
    }


def get_stats() -> dict[str, typing.Any]:
    try:
        disk_usage_stats = get_disk_usage_stats()
    except Exception:
        _LOGGER.exception("Failed to get disk usage stats")
        disk_usage_stats = None

    try:
        load_average_stats = get_load_average_stats()
    except Exception:
        _LOGGER.exception("Failed to get load average stats")
        load_average_stats = None

    try:
        memory_stats = get_memory_stats()
    except Exception:
        _LOGGER.exception("Failed to get memory stats")
        memory_stats = None

    try:
        uptime = get_uptime()
    except Exception:
        _LOGGER.exception("Failed to get uptime")
        uptime = None

    return {
        "disk_usage": disk_usage_stats,
        "load_average": load_average_stats,
        "memory": memory_stats,
        "uptime": uptime,
    }


def get_release() -> str:
    try:
        puavo_os_image_name = ktp_controller.utils.readfirstline(
            "/etc/puavo-image/name"
        )
        puavo_os_image_release = ktp_controller.utils.readfirstline(
            "/etc/puavo-image/release"
        )
    except Exception:
        _LOGGER.exception(
            "Failed to find out the release information of the current OS"
        )
        return "unknown"

    return f"{puavo_os_image_release} ({puavo_os_image_name})"
