"""
Manage nginx
"""

# Standard library imports
import logging
import os
import os.path
import subprocess

# Internal imports
import ktp_controller.utils

__all__ = [
    "disable_nginx_wui_tls_reverse_proxy",
    "enable_nginx_wui_tls_reverse_proxy",
]


_LOGGER = logging.getLogger(__name__)

NGINX_DIRPATH = "/etc/nginx"
NGINX_SITES_AVAILABLE_DIRPATH = os.path.join(NGINX_DIRPATH, "sites-available")
NGINX_SITES_ENABLED_DIRPATH = os.path.join(NGINX_DIRPATH, "sites-enabled")
NGINX_WUI_SITE_NAME = "ktp-controller-wui"
NGINX_WUI_CRT_FILEPATH = os.path.join(NGINX_DIRPATH, "ktp-controller-wui.crt")
NGINX_WUI_KEY_FILEPATH = os.path.join(NGINX_DIRPATH, "ktp-controller-wui.key")

WUI_UPSTREAM_URL = "http://127.0.0.1:9999"


def disable_nginx_wui_tls_reverse_proxy() -> None:
    """Deconfigure nginx as a TLS terminating reverse proxy in front
    of WUI.

    Counter part to `enable_nginx_wui_tls_reverse_proxy()`.
    """

    enabled_symlink_filepath = os.path.join(
        NGINX_SITES_ENABLED_DIRPATH, NGINX_WUI_SITE_NAME
    )
    site_filepath = os.path.join(NGINX_SITES_AVAILABLE_DIRPATH, NGINX_WUI_SITE_NAME)

    try:
        os.remove(enabled_symlink_filepath)
    except FileNotFoundError:
        _LOGGER.warning(
            "Nginx site %r does not exist, nginx reconfiguration skipped",
            _PATHS.wui_site_name,
        )
        return

    _LOGGER.info("Deleted %r", enabled_symlink_filepath)

    exceptions = []
    try:
        for fp in [NGINX_WUI_KEY_FILEPATH, NGINX_WUI_CRT_FILEPATH, site_filepath]:
            try:
                os.remove(site_filepath)
            except Exception as e:
                exceptions.append(e)
                continue
            _LOGGER.info("Deleted %r", fp)
    finally:
        subprocess.check_call(["systemctl", "reload", "nginx"])
        _LOGGER.info("Reloaded nginx")

    if exceptions:
        raise ExceptionGroup(
            "failed to delete some of the WUI's files from /etc/nginx",
            exceptions,
        )

    _LOGGER.info("Deconfigured Nginx site %r", _PATHS.wui_site_name)


def enable_nginx_wui_tls_reverse_proxy(
    domain_name: str, port: int, crt_filepath: str, key_filepath: str
) -> None:
    """Configure nginx as a TLS terminating reverse proxy in front of
    WUI (listening at WUI_UPSTREAM_URL), making WUI reachable at
    https://<domain_name>:<port>/.

    crt_filepath and key_filepath are copied into NGINX_DIRPATH so the
    TLS certificate and key remain available even if the original
    files are deleted afterwards.

    """

    ktp_controller.utils.copy_atomic(crt_filepath, NGINX_WUI_CRT_FILEPATH)
    ktp_controller.utils.copy_atomic(key_filepath, NGINX_WUI_KEY_FILEPATH)

    config = f"""\
server {{
    listen {port} ssl;
    server_name {domain_name};

    ssl_certificate {NGINX_WUI_CRT_FILEPATH};
    ssl_certificate_key {NGINX_WUI_KEY_FILEPATH};

    location / {{
        proxy_pass {WUI_UPSTREAM_URL};
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
}}
"""

    site_filepath = os.path.join(NGINX_SITES_AVAILABLE_DIRPATH, NGINX_WUI_SITE_NAME)
    enabled_symlink_filepath = os.path.join(
        NGINX_SITES_ENABLED_DIRPATH, NGINX_WUI_SITE_NAME
    )

    with ktp_controller.utils.open_atomic_write(
        site_filepath, encoding="utf-8"
    ) as site_file:
        site_file.write(config)

    symlink_target = os.path.relpath(site_filepath, NGINX_SITES_ENABLED_DIRPATH)
    try:
        os.symlink(symlink_target, enabled_symlink_filepath)
    except FileExistsError:
        os.remove(enabled_symlink_filepath)
        os.symlink(symlink_target, enabled_symlink_filepath)

    completed_process = subprocess.run(
        ["systemctl", "reload", "nginx"], capture_output=True
    )
    if completed_process.returncode != 0:
        _LOGGER.error("failed to reload nginx: %s", completed_process.stderr.decode())
