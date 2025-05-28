import random
import string
import logging
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("registration_test_fast.log"), logging.StreamHandler()],
)


class FastRegistrationTester:
    """A leaner, faster version of the registration tester that now waits
    for a 4‑digit verification code before clicking the Register button.
    The code field is polled once per second, for up to ``CODE_INPUT_TIMEOUT``
    seconds. Adjust ``CODE_FIELD_ID`` below if your page uses a different
    element ID or a CSS selector.
    """

    # ------------------------------------------------------------------
    # Global settings
    # ------------------------------------------------------------------
    DEFAULT_TIMEOUT = 10           # seconds for explicit waits
    POLL_FREQUENCY = 0.3           # seconds for WebDriverWait polling
    CODE_INPUT_TIMEOUT = 120       # seconds to wait for a 4‑digit code
    CODE_FIELD_ID = "register-code"  # ID of the verification‑code <input>

    def __init__(self, url: str = "https://node1.much-ai.com", headless: bool = False):
        self.url = url.rstrip("/")
        self.headless = headless
        self.driver = self._setup_driver()
        self.wait = WebDriverWait(
            self.driver, self.DEFAULT_TIMEOUT, poll_frequency=self.POLL_FREQUENCY
        )

    # ------------------------------------------------------------------
    # Driver helpers
    # ------------------------------------------------------------------
    def _setup_driver(self):
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        # Faster, lighter‑weight browsing
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--blink-settings=imagesEnabled=false")  # block images
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.page_load_strategy = "eager"  # don't wait for images/ads
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(self.DEFAULT_TIMEOUT)
        return driver

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _random_email() -> str:
        base = random.choice(
            [
                "forsystemxu@gmail.com",
                "raoxu1314@gmail.com",
                "xhrry1314@gmail.com",
            ]
        )
        local = base.split("@")[0]
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{local}+{suffix}@gmail.com"

    # ------------------------------------------------------------------
    # Core workflow
    # ------------------------------------------------------------------
    def run(self):
        start = datetime.now()
        data = {"email": self._random_email(), "password": "qqq123456"}
        logging.info("Generated email %s", data["email"])

        try:
            self.driver.get(self.url)
            self._close_notifications()
            self._go_to_register_tab()
            self._fill_form(data)

            if self._wait_for_code_input():
                self._submit()
            else:
                logging.error("Verification code not entered within %ss", self.CODE_INPUT_TIMEOUT)
                return {
                    "status": "timeout",
                    "message": "验证码超时未输入",
                    "url": self.driver.current_url,
                }

            result = self._check_result()
        finally:
            # Always capture evidence fast
            snap = f"reg_fast_{start.strftime('%Y%m%d_%H%M%S')}.png"
            try:
                self.driver.save_screenshot(snap)
            except Exception:
                pass
            self.driver.quit()

        duration = (datetime.now() - start).total_seconds()
        result["duration"] = duration
        logging.info("Finished in %.2fs", duration)
        return result

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------
    def _close_notifications(self):
        try:
            ok = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[contains(@class, 'el-button--primary') and .//span[text()='OK']]",
                    )
                )
            )
            ok.click()
            logging.info("Closed notification pop‑up")
        except TimeoutException:
            logging.debug("No notification pop‑up detected")

    def _go_to_register_tab(self):
        login_btn = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='登录']]"))
        )
        login_btn.click()
        register_tab = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//div[@id='tab-register' and contains(@class,'el-tabs__item')]",
                )
            )
        )
        register_tab.click()
        logging.info("Switched to register tab")

    def _fill_form(self, data):
        # E‑mail / phone
        self.wait.until(EC.presence_of_element_located((By.ID, "register-phone"))).send_keys(
            data["email"]
        )
        # Send code
        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='发送验证码']]"))
        ).click()
        # Passwords
        self.wait.until(EC.presence_of_element_located((By.ID, "register-password"))).send_keys(
            data["password"]
        )
        self.wait.until(
            EC.presence_of_element_located((By.ID, "register-confirm-password"))
        ).send_keys(data["password"])
        logging.info("Form filled – waiting for verification code input…")

    def _wait_for_code_input(self) -> bool:
        """Poll the verification‑code input every second until 4 digits are
        entered or the timeout expires. Returns ``True`` when 4 digits are
        detected, otherwise ``False``.
        """
        end_time = time.time() + self.CODE_INPUT_TIMEOUT
        while time.time() < end_time:
            try:
                code_input = self.driver.find_element(By.ID, self.CODE_FIELD_ID)
                value = (code_input.get_attribute("value") or "").strip()
                if len(value) == 4 and value.isdigit():
                    logging.info("Detected 4‑digit code: %s", value)
                    return True
            except Exception:
                # Element not ready / transient – ignore and retry
                pass
            time.sleep(1)  # poll once per second
        return False

    def _submit(self):
        self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(@class,'el-button--primary') and .//span[text()='注册']]",
                )
            )
        ).click()
        logging.info("Clicked register")

    def _check_result(self):
        time.sleep(2)  # short settle
        current_url = self.driver.current_url
        logging.info("Redirected to %s", current_url)
        if any(k in current_url.lower() for k in ["success", "dashboard", "home", "welcome"]):
            status = "success"
            msg = "注册成功"
        else:
            # Try pick up toast message quickly (non‑blocking)
            try:
                toast = self.driver.find_element(By.CSS_SELECTOR, "div.el-message").text.strip()
                status = "error" if toast else "unknown"
                msg = toast or "无法确定注册结果"
            except Exception:
                status = "unknown"
                msg = "无法确定注册结果"
        return {"status": status, "message": msg, "url": current_url}


if __name__ == "__main__":
    tester = FastRegistrationTester(headless=False)
    outcome = tester.run()
    print("RESULT:", outcome)
