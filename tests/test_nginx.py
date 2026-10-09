import os
import os.path
import subprocess

import ktp_controller.nginx


def _patch_nginx_dirs(monkeypatch, testdir):
    nginx_dirpath = os.path.join(testdir, "etc-nginx")
    sites_available_dirpath = os.path.join(nginx_dirpath, "sites-available")
    sites_enabled_dirpath = os.path.join(nginx_dirpath, "sites-enabled")

    os.makedirs(sites_available_dirpath)
    os.makedirs(sites_enabled_dirpath)

    monkeypatch.setattr(ktp_controller.nginx, "NGINX_DIRPATH", nginx_dirpath)
    monkeypatch.setattr(
        ktp_controller.nginx, "NGINX_SITES_AVAILABLE_DIRPATH", sites_available_dirpath
    )
    monkeypatch.setattr(
        ktp_controller.nginx, "NGINX_SITES_ENABLED_DIRPATH", sites_enabled_dirpath
    )

    return nginx_dirpath, sites_available_dirpath, sites_enabled_dirpath


def _write(filepath, content):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def test_setup_nginx_wui_tls_reverse_proxy(monkeypatch, mocker, testdir):
    nginx_dirpath, sites_available_dirpath, sites_enabled_dirpath = _patch_nginx_dirs(
        monkeypatch, testdir
    )

    crt_filepath = os.path.join(testdir, "exam.crt")
    key_filepath = os.path.join(testdir, "exam.key")
    _write(crt_filepath, "dummy-cert")
    _write(key_filepath, "dummy-key")

    run_mock = mocker.patch(
        "ktp_controller.nginx.subprocess.run",
        return_value=subprocess.CompletedProcess(args=[], returncode=0),
    )

    ktp_controller.nginx.setup_nginx_wui_tls_reverse_proxy(
        "exam.example.invalid", 8443, crt_filepath, key_filepath
    )

    dest_crt_filepath = os.path.join(nginx_dirpath, "exam.crt")
    dest_key_filepath = os.path.join(nginx_dirpath, "exam.key")
    with open(dest_crt_filepath, encoding="utf-8") as f:
        assert f.read() == "dummy-cert"
    with open(dest_key_filepath, encoding="utf-8") as f:
        assert f.read() == "dummy-key"

    site_filepath = os.path.join(sites_available_dirpath, "ktp-controller-wui")
    with open(site_filepath, encoding="utf-8") as f:
        config = f.read()
    assert "listen 8443 ssl;" in config
    assert "server_name exam.example.invalid;" in config
    assert f"ssl_certificate {dest_crt_filepath};" in config
    assert f"ssl_certificate_key {dest_key_filepath};" in config
    assert "proxy_pass http://127.0.0.1:9999;" in config
    # $host strips the port from the forwarded Host header, which
    # breaks absolute redirects (e.g. Starlette's trailing-slash
    # redirect) when WUI is served on a non-standard port.
    assert "proxy_set_header Host $http_host;" in config

    enabled_symlink_filepath = os.path.join(sites_enabled_dirpath, "ktp-controller-wui")
    assert os.path.islink(enabled_symlink_filepath)
    assert os.path.realpath(enabled_symlink_filepath) == os.path.realpath(site_filepath)

    run_mock.assert_called_once_with(
        ["systemctl", "reload", "nginx"], capture_output=True
    )


def test_setup_nginx_wui_tls_reverse_proxy_replaces_existing_symlink(
    monkeypatch, mocker, testdir
):
    _nginx_dirpath, sites_available_dirpath, sites_enabled_dirpath = _patch_nginx_dirs(
        monkeypatch, testdir
    )

    crt_filepath = os.path.join(testdir, "exam.crt")
    key_filepath = os.path.join(testdir, "exam.key")
    _write(crt_filepath, "dummy-cert")
    _write(key_filepath, "dummy-key")

    stale_target_filepath = os.path.join(testdir, "stale")
    _write(stale_target_filepath, "stale")
    enabled_symlink_filepath = os.path.join(sites_enabled_dirpath, "ktp-controller-wui")
    os.symlink(stale_target_filepath, enabled_symlink_filepath)

    mocker.patch(
        "ktp_controller.nginx.subprocess.run",
        return_value=subprocess.CompletedProcess(args=[], returncode=0),
    )

    ktp_controller.nginx.setup_nginx_wui_tls_reverse_proxy(
        "exam.example.invalid", 8443, crt_filepath, key_filepath
    )

    site_filepath = os.path.join(sites_available_dirpath, "ktp-controller-wui")
    assert os.path.realpath(enabled_symlink_filepath) == os.path.realpath(site_filepath)


def test_setup_nginx_wui_tls_reverse_proxy_logs_warning_on_reload_failure(
    monkeypatch, mocker, testdir
):
    _patch_nginx_dirs(monkeypatch, testdir)

    crt_filepath = os.path.join(testdir, "exam.crt")
    key_filepath = os.path.join(testdir, "exam.key")
    _write(crt_filepath, "dummy-cert")
    _write(key_filepath, "dummy-key")

    mocker.patch(
        "ktp_controller.nginx.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=1, stderr=b"nginx: configuration file test failed"
        ),
    )
    warning_mock = mocker.patch.object(ktp_controller.nginx._LOGGER, "warning")

    ktp_controller.nginx.setup_nginx_wui_tls_reverse_proxy(
        "exam.example.invalid", 8443, crt_filepath, key_filepath
    )

    warning_mock.assert_called_once()
