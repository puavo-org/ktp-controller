# Standard library imports

# Third-party imports
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Internal imports

# Relative imports
from .utils import random_artificial_hetu


class _Base:
    def __init__(self, browser):
        self.browser = browser
        self.wait = WebDriverWait(browser, 10)

    def find(self, locator):
        return self.wait.until(EC.visibility_of_element_located(locator))

    def find_not(self, locator):
        return self.wait.until_not(EC.visibility_of_element_located(locator))

    def click(self, locator):
        self.wait.until(EC.element_to_be_clickable(locator)).click()

    def enter_text(self, locator, text):
        self.find(locator).send_keys(text)


def _button_by_text(text):
    return (By.XPATH, f'//button[text()="{text}"]')


class Abitti2Student(_Base):
    def _radio_button_by_name_and_value(self, name, value):
        escaped_value = self.browser.execute_script(
            "return CSS.escape(arguments[0]);", value
        )

        return (
            By.CSS_SELECTOR,
            f'input[type="radio"][name="{name}"][value="{escaped_value}"]',
        )

    def load(self):
        self.browser.get("https://asiasana-vahinko.koe.abitti.net:8010/")

    def accept_eula(self):
        self.click(_button_by_text("Hyväksyn käyttöehdot ja valvonnan"))

    def register(self, *, first_name, last_name, ssn, email):
        self.enter_text((By.ID, "firstNames"), first_name)
        self.enter_text((By.ID, "lastName"), last_name)
        self.enter_text((By.ID, "ssn"), ssn)
        self.enter_text((By.ID, "email"), email)
        self.click(_button_by_text("Siirry kokeen valintaan"))

    def select_exam(self, *, exam_uuid):
        self.click(self._radio_button_by_name_and_value("exam-language", "fi-FI"))
        self.click(self._radio_button_by_name_and_value("exam", exam_uuid))
        self.click(_button_by_text("Vahvista koevalinta"))

    def enter_access_code(self, *, access_code):
        self.find_not((By.CSS_SELECTOR, 'div[data-testid="wait-for-approval"]'))

        keycode, authcode = access_code
        for i, c in enumerate(keycode):
            self.enter_text((By.ID, f"keycode-input-{i}"), c)
        for i, c in enumerate(authcode):
            self.enter_text((By.ID, f"autorization-code-input-{i}"), c)  # Typo by YTL

        self.find((By.CSS_SELECTOR, 'div[data-testid="wait-for-approval"]'))

    def start_exam(self, *, exam_uuid, exam_title, access_code):
        self.load()
        self.accept_eula()
        hetu = random_artificial_hetu()
        self.register(
            first_name="Tester",
            last_name="Tester",
            ssn=hetu,
            email=f"tester.tester.{hetu}@test.invalid",  # RF2606 reserves .invalid
        )
        self.select_exam(exam_uuid=exam_uuid)
        self.enter_access_code(access_code=access_code)
        self.click((By.CSS_SELECTOR, 'button[data-testid="close-exam-instructions"]'))
        self.find(
            (
                By.XPATH,
                f"//h1[@id='title' and contains(text(), '{exam_title}')]",
            )
        )
