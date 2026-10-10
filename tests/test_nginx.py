import os
import os.path
import subprocess

import pytest

import ktp_controller.nginx
from ktp_controller import SETTINGS


def _patch_nginx_paths(monkeypatch, testdir):
    paths = ktp_controller.nginx._Paths(
        root_conf_dirpath=os.path.join(testdir, "etc-nginx")
    )

    os.makedirs(paths.sites_available_dirpath)
    os.makedirs(paths.sites_enabled_dirpath)

    monkeypatch.setattr(ktp_controller.nginx, "_PATHS", paths)

    return paths


def _write(filepath, content):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def test_enable_nginx_wui_tls_reverse_proxy(monkeypatch, mocker, testdir):
    paths = _patch_nginx_paths(monkeypatch, testdir)

    crt_filepath = os.path.join(testdir, "exam.crt")
    key_filepath = os.path.join(testdir, "exam.key")
    _write(crt_filepath, "dummy-cert")
    _write(key_filepath, "dummy-key")

    run_mock = mocker.patch(
        "ktp_controller.nginx.subprocess.check_call", return_value=None
    )

    ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy(
        "exam.example.invalid", 8443, crt_filepath, key_filepath
    )

    dest_crt_filepath = os.path.join(paths.root_conf_dirpath, "ktp-controller-wui.crt")
    dest_key_filepath = os.path.join(paths.root_conf_dirpath, "ktp-controller-wui.key")
    with open(dest_crt_filepath, encoding="utf-8") as f:
        assert f.read() == "dummy-cert"
    with open(dest_key_filepath, encoding="utf-8") as f:
        assert f.read() == "dummy-key"

    site_filepath = os.path.join(paths.sites_available_dirpath, "ktp-controller-wui")
    with open(site_filepath, encoding="utf-8") as f:
        config = f.read()
    assert "listen 8443 ssl;" in config
    assert "server_name exam.example.invalid;" in config
    assert f"ssl_certificate {dest_crt_filepath};" in config
    assert f"ssl_certificate_key {dest_key_filepath};" in config
    assert f"proxy_pass http://{SETTINGS.wui_host}:{SETTINGS.wui_port};" in config
    # $host strips the port from the forwarded Host header, which
    # breaks absolute redirects (e.g. Starlette's trailing-slash
    # redirect) when WUI is served on a non-standard port.
    assert "proxy_set_header Host $http_host;" in config

    enabled_symlink_filepath = os.path.join(
        paths.sites_enabled_dirpath, "ktp-controller-wui"
    )
    assert os.path.islink(enabled_symlink_filepath)
    assert os.path.realpath(enabled_symlink_filepath) == os.path.realpath(site_filepath)

    run_mock.assert_called_once_with(["systemctl", "reload", "nginx"])


def test_enable_nginx_wui_tls_reverse_proxy_replaces_existing_symlink(
    monkeypatch, mocker, testdir
):
    paths = _patch_nginx_paths(monkeypatch, testdir)

    crt_filepath = os.path.join(testdir, "ktp-controller-wui.crt")
    key_filepath = os.path.join(testdir, "ktp-controller-wui.key")
    _write(crt_filepath, "dummy-cert")
    _write(key_filepath, "dummy-key")

    stale_target_filepath = os.path.join(testdir, "stale")
    _write(stale_target_filepath, "stale")
    enabled_symlink_filepath = os.path.join(
        paths.sites_enabled_dirpath, "ktp-controller-wui"
    )
    os.symlink(stale_target_filepath, enabled_symlink_filepath)

    mocker.patch("ktp_controller.nginx.subprocess.check_call", return_value=None)

    ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy(
        "exam.example.invalid", 8443, crt_filepath, key_filepath
    )

    site_filepath = os.path.join(paths.sites_available_dirpath, "ktp-controller-wui")
    assert os.path.realpath(enabled_symlink_filepath) == os.path.realpath(site_filepath)


def test_enable_nginx_wui_tls_reverse_proxy_raises_exception_on_reload_failure(
    monkeypatch, mocker, testdir
):
    _patch_nginx_paths(monkeypatch, testdir)

    crt_filepath = os.path.join(testdir, "ktp-controller-wui.crt")
    key_filepath = os.path.join(testdir, "ktp-controller-wui.key")
    _write(crt_filepath, "dummy-cert")
    _write(key_filepath, "dummy-key")

    mocker.patch(
        "ktp_controller.nginx.subprocess.check_call",
        side_effect=subprocess.CalledProcessError(1, ["systemctl", "reload", "nginx"]),
    )

    with pytest.raises(subprocess.CalledProcessError):
        ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy(
            "exam.example.invalid", 8443, crt_filepath, key_filepath
        )
