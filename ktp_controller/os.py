import logging
import time
import psutil

_LOGGER = logging.getLogger(__name__)


def get_uptime() -> float:
    # Uptime is current time minus boot time
    return time.time() - psutil.boot_time()


def get_disk_usage_stats() -> list:
    stats = []

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


def get_load_average_stats() -> dict:
    load1, load5, load15 = psutil.getloadavg()
    return {
        "1min": load1,
        "5min": load5,
        "15min": load15,
    }


def get_memory_stats() -> dict:
    mem = psutil.virtual_memory()
    return {
        "total": mem.total,
        "used": mem.used,
        "free": mem.free,
        "available": mem.available,
    }


def get_stats() -> dict:
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
