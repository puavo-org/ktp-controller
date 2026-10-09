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
    "setup_nginx_wui_tls_reverse_proxy",
]


_LOGGER = logging.getLogger(__name__)

NGINX_DIRPATH = "/etc/nginx"
NGINX_SITES_AVAILABLE_DIRPATH = os.path.join(NGINX_DIRPATH, "sites-available")
NGINX_SITES_ENABLED_DIRPATH = os.path.join(NGINX_DIRPATH, "sites-enabled")
NGINX_WUI_SITE_NAME = "ktp-controller-wui"
WUI_UPSTREAM_URL = "http://127.0.0.1:9999"


def setup_nginx_wui_tls_reverse_proxy(
    domain_name: str, port: int, crt_filepath: str, key_filepath: str
) -> None:
    """Configure nginx as a TLS terminating reverse proxy in front of
    WUI (listening at WUI_UPSTREAM_URL), making WUI reachable at
    https://<domain_name>:<port>/.

    crt_filepath and key_filepath are copied into NGINX_DIRPATH so the
    TLS certificate and key remain available even if the original
    files are deleted afterwards.

    """
    dest_crt_filepath = os.path.join(NGINX_DIRPATH, os.path.basename(crt_filepath))
    dest_key_filepath = os.path.join(NGINX_DIRPATH, os.path.basename(key_filepath))

    ktp_controller.utils.copy_atomic(crt_filepath, dest_crt_filepath)
    ktp_controller.utils.copy_atomic(key_filepath, dest_key_filepath)

    config = f"""\
server {{
    listen {port} ssl;
    server_name {domain_name};

    ssl_certificate {dest_crt_filepath};
    ssl_certificate_key {dest_key_filepath};

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
