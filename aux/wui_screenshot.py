"""Log into a running WUI (e.g. `./dev-run`) and save screenshots of pages.

Handy for visually reviewing CSS/template changes without a full browser
session. Requires the `selenium` dev dependency (already declared in
pyproject.toml) and a Chromium/Chrome binary on PATH.

Example:
    uv run aux/wui_screenshot.py \\
        --username valvoja --password '...' \\
        /invigilator/ /invigilator/student_access_code /
"""

import argparse
import pathlib
import shutil
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def _find_chromium_binary() -> str | None:
    for name in ("chromium", "chromium-browser", "google-chrome"):
        path = shutil.which(name)
        if path:
            return path
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:19999")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=pathlib.Path("workdirs/dev/screenshots"),
    )
    parser.add_argument(
        "--expand-details",
        action="store_true",
        help="Open every <details> element on the page before capturing.",
    )
    parser.add_argument(
        "paths", nargs="+", help="WUI paths to screenshot, e.g. /invigilator/"
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    options = Options()
    binary = _find_chromium_binary()
    if binary:
        options.binary_location = binary
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,1000")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(f"{args.base_url}/login")
        driver.find_element(By.NAME, "username").send_keys(args.username)
        driver.find_element(By.NAME, "password").send_keys(args.password)
        driver.find_element(
            By.CSS_SELECTOR, "form[action*='/login'] button[type=submit]"
        ).click()
        time.sleep(1)

        for path in args.paths:
            driver.get(f"{args.base_url}{path}")
            time.sleep(1)
            if args.expand_details:
                for details in driver.find_elements(By.CSS_SELECTOR, "details"):
                    driver.execute_script("arguments[0].open = true;", details)
                time.sleep(0.3)
            height = driver.execute_script("return document.body.scrollHeight")
            driver.set_window_size(1400, max(height, 1000))
            time.sleep(0.2)
            out_path = args.out_dir / (path.strip("/").replace("/", "_") or "index")
            out_path = out_path.with_suffix(".png")
            driver.save_screenshot(str(out_path))
            print(f"{path} -> {out_path}")
    finally:
        driver.quit()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
