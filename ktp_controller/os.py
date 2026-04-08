import time
import psutil


def get_uptime() -> float:
    # Uptime is current time minus boot time
    return time.time() - psutil.boot_time()


def get_disk_usage_stats() -> dict:
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
    return {
        "disk_usage": get_disk_usage_stats(),
        "load_average": get_load_average_stats(),
        "memory": get_memory_stats(),
        "uptime": get_uptime(),
    }
