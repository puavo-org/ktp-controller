"""
Manage nginx
"""

# Standard library imports
import logging
import os
import os.path
import subprocess

# Internal imports
import ktp_controller.os
import ktp_controller.utils
from ktp_controller import SETTINGS

__all__ = [
    "disable_nginx_wui_tls_reverse_proxy",
    "enable_nginx_wui_tls_reverse_proxy",
]


_LOGGER = logging.getLogger(__name__)

WUI_UPSTREAM_URL = f"http://{SETTINGS.wui_host}:{SETTINGS.wui_port}"

PUAVO_HOST_CRT_FILEPATH = "/etc/puavo/certs/host.crt"
PUAVO_HOST_KEY_FILEPATH = "/etc/puavo/certs/host.key"


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
        self.wui_puavo_crt_filepath = os.path.join(
            root_conf_dirpath, "ktp-controller-wui-puavo.crt"
        )
        self.wui_puavo_key_filepath = os.path.join(
            root_conf_dirpath, "ktp-controller-wui-puavo.key"
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

        # Only present when the site was enabled with a Puavo fqdn;
        # absence here is normal, not a partial-failure condition.
        for fp in [_PATHS.wui_puavo_key_filepath, _PATHS.wui_puavo_crt_filepath]:
            try:
                os.remove(fp)
            except FileNotFoundError:
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
    https://<domain_name>:<port>/ and, when this host has a Puavo fqdn
    (ktp_controller.os.get_puavo_fqdn()), also at
    https://<puavo_fqdn>:<port>/.

    crt_filepath and key_filepath (and the Puavo host cert/key, when
    applicable) are copied into _PATHS.ROOT_CONF_DIRPATH so the TLS
    certificates and keys remain available even if the original
    files are deleted afterwards.

    """

    server_domains = [
        (
            domain_name,
            crt_filepath,
            key_filepath,
            _PATHS.wui_crt_filepath,
            _PATHS.wui_key_filepath,
        ),
    ]

    puavo_fqdn = ktp_controller.os.get_puavo_fqdn()
    if puavo_fqdn is not None:
        server_domains.append(
            (
                puavo_fqdn,
                PUAVO_HOST_CRT_FILEPATH,
                PUAVO_HOST_KEY_FILEPATH,
                _PATHS.wui_puavo_crt_filepath,
                _PATHS.wui_puavo_key_filepath,
            )
        )

    for _, crt_src, key_src, crt_dest, key_dest in server_domains:
        ktp_controller.utils.copy_atomic(crt_src, crt_dest, modebits=0o0444)
        ktp_controller.utils.copy_atomic(key_src, key_dest, modebits=0o0400)

    proxy_headers = """\
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
"""

    def _render_server_block(
        server_domain_name: str, crt_dest: str, key_dest: str
    ) -> str:
        return f"""\
server {{
    listen {port} ssl;
    server_name {server_domain_name};

    ssl_certificate {crt_dest};
    ssl_certificate_key {key_dest};

    # Some front doors (e.g. Exam-O-Matic) route a browser in through a
    # volatile "/remote/<id>" prefix that selects this particular
    # KTP Controller instance, without rewriting the path themselves.
    # Forward the request to WUI with its path UNCHANGED (ASGI's
    # root_path mechanism expects the full, un-stripped path - Starlette
    # recomputes each route's/mount's relative path on the fly by
    # subtracting root_path, rather than relying on it having already
    # been stripped) and tell WUI what the prefix is via
    # X-Forwarded-Prefix, so it can render prefix-correct links back to
    # the browser (see ktp_controller.wui.middleware.
    # RootPathFromHeaderMiddleware). WUI itself is reachable this way
    # as well as via the unprefixed "/" location below.
    location ~ ^/remote/([0-9]+)$ {{
        return 308 /remote/$1/;
    }}

    location ~ ^/remote/([0-9]+)/ {{
        proxy_pass {WUI_UPSTREAM_URL};
{proxy_headers}\
        proxy_set_header X-Forwarded-Prefix /remote/$1;
    }}

    location / {{
        proxy_pass {WUI_UPSTREAM_URL};
{proxy_headers}\
    }}
}}
"""

    config = "\n".join(
        _render_server_block(server_domain_name, crt_dest, key_dest)
        for server_domain_name, _, _, crt_dest, key_dest in server_domains
    )

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
