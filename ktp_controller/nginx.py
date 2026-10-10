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
from ktp_controller import SETTINGS

__all__ = [
    "disable_nginx_wui_tls_reverse_proxy",
    "enable_nginx_wui_tls_reverse_proxy",
]


_LOGGER = logging.getLogger(__name__)

WUI_UPSTREAM_URL = f"http://{SETTINGS.wui_host}:{SETTINGS.wui_port}"


class _Paths:
    def __init__(self, *, root_conf_dirpath: str = "/etc/nginx"):
        self.root_conf_dirpath = root_conf_dirpath
        self.sites_available_dirpath = os.path.join(
            root_conf_dirpath, "sites-available"
        )
        self.sites_enabled_dirpath = os.path.join(root_conf_dirpath, "sites-enabled")
        self.wui_site_name = "ktp-controller-wui"
        self.wui_crt_filepath = os.path.join(
            root_conf_dirpath, "ktp-controller-wui.crt"
        )
        self.wui_key_filepath = os.path.join(
            root_conf_dirpath, "ktp-controller-wui.key"
        )
        self.wui_site_filepath = os.path.join(
            self.sites_available_dirpath, self.wui_site_name
        )
        self.wui_symlink_filepath = os.path.join(
            self.sites_enabled_dirpath, self.wui_site_name
        )
        self.wui_symlink_target = os.path.relpath(
            self.wui_site_filepath, self.sites_enabled_dirpath
        )


_PATHS = _Paths()


def disable_nginx_wui_tls_reverse_proxy() -> None:
    """Deconfigure nginx as a TLS terminating reverse proxy in front
    of WUI.

    Counter part to `enable_nginx_wui_tls_reverse_proxy()`.
    """

    try:
        os.remove(_PATHS.wui_symlink_filepath)
    except FileNotFoundError:
        _LOGGER.warning(
            "Nginx site %r does not exist, nginx reconfiguration skipped",
            _PATHS.wui_site_name,
        )
        return

    _LOGGER.info("Deleted %r", _PATHS.wui_symlink_filepath)

    exceptions = []
    try:
        for fp in [
            _PATHS.wui_key_filepath,
            _PATHS.wui_crt_filepath,
            _PATHS.wui_site_filepath,
        ]:
            try:
                os.remove(fp)
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

    crt_filepath and key_filepath are copied into _PATHS.ROOT_CONF_DIRPATH so the
    TLS certificate and key remain available even if the original
    files are deleted afterwards.

    """

    ktp_controller.utils.copy_atomic(crt_filepath, _PATHS.wui_crt_filepath)
    ktp_controller.utils.copy_atomic(key_filepath, _PATHS.wui_key_filepath)

    config = f"""\
server {{
    listen {port} ssl;
    server_name {domain_name};

    ssl_certificate {_PATHS.wui_crt_filepath};
    ssl_certificate_key {_PATHS.wui_key_filepath};

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

    with ktp_controller.utils.open_atomic_write(
        _PATHS.wui_site_filepath, encoding="utf-8"
    ) as site_file:
        site_file.write(config)

    try:
        os.symlink(_PATHS.wui_symlink_target, _PATHS.wui_symlink_filepath)
    except FileExistsError:
        os.remove(_PATHS.wui_symlink_filepath)
        os.symlink(_PATHS.wui_symlink_target, _PATHS.wui_symlink_filepath)

    subprocess.check_call(["systemctl", "reload", "nginx"])

    _LOGGER.info("Configured Nginx site %r", _PATHS.wui_site_name)
