
import random
import string
import logging
import time
from datetime import datetime

from appium import webdriver  # Appium drives the Android browser
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
    """专为 **华为浏览器** 预设的快速注册自动化脚本。

    ▶ 默认包名 `com.huawei.browser`
    ▶ 默认主 Activity `com.huawei.browser.BrowserActivity`

    只需安装 Appium‑Server、匹配版本的 chromedriver，并连上开启 USB 调试的华为/荣耀手机即可运行。
    """

    DEFAULT_TIMEOUT = 10         # 显式等待秒数
    POLL_FREQUENCY = 0.3         # WebDriverWait 轮询间隔
    CODE_LEN = 4                 # 验证码位数
    MAX_CODE_WAIT = 300          # 最多等待验证码秒数

    def __init__(
        self,
        url: str = "https://node1.much-ai.com",
        headless: bool = False,
        browser_package: str = "com.huawei.browser",
        browser_activity: str = "com.huawei.browser.BrowserActivity",
        appium_server: str = "http://127.0.0.1:4723/wd/hub",
    ):
        self.url = url.rstrip("/")
        self.headless = headless
        self.browser_package = browser_package
        self.browser_activity = browser_activity
        self.appium_server = appium_server

        self.driver = self._setup_driver()
        self.wait = WebDriverWait(
            self.driver, self.DEFAULT_TIMEOUT, poll_frequency=self.POLL_FREQUENCY
        )

    # ------------------------------------------------------------------
    # Driver helpers
    # ------------------------------------------------------------------
    def _setup_driver(self):
        caps = {
            "platformName": "Android",
            "appium:automationName": "UiAutomator2",
            "appium:deviceName": "Android",  # 名称随意
            "appium:newCommandTimeout": 600,
            # 指定包名 / Activity
            "appium:appPackage": self.browser_package,
            "appium:appActivity": self.browser_activity,
            # 关闭图片，提速
            "appium:chromeOptions": {"args": ["--blink-settings=imagesEnabled=false"]},
            # 如果用 Chrome‑based 内核，可加 chromedriverExecutable 路径；省事可靠 Appium 自动下载
        }
        driver = webdriver.Remote(self.appium_server, caps)
        driver.implicitly_wait(self.DEFAULT_TIMEOUT)
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
            self._submit()
            result = self._check_result()
        finally:
            snap = f"reg_fast_{start.strftime('%Y%m%d_%H%M%S')}.png"
            try:
                self.driver.save_screenshot(snap)
            except Exception:
                pass
            self.driver.quit()

        result["duration"] = (datetime.now() - start).total_seconds()
        logging.info("Finished in %.2fs", result["duration"])
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
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='登录']]"))).click()
        self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@id='tab-register' and contains(@class,'el-tabs__item')]")
            )
        ).click()
        logging.info("Switched to register tab")

    def _fill_form(self, data):
        self.wait.until(EC.presence_of_element_located((By.ID, "register-phone"))).send_keys(data["email"])
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='发送验证码']]"))).click()
        self.wait.until(EC.presence_of_element_located((By.ID, "register-password"))).send_keys(data["password"])
        self.wait.until(EC.presence_of_element_located((By.ID, "register-confirm-password"))).send_keys(data["password"])
        print("\n已发送验证码，请在网页输入 4 位数字验证码…\n")
        self._wait_for_code()

    def _wait_for_code(self):
        start_time = time.time()
        while True:
            code_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            for inp in code_inputs:
                if inp.is_displayed() and inp.get_attribute("id") != "register-phone":
                    val = inp.get_attribute("value").strip()
                    if len(val) == self.CODE_LEN and val.isdigit():
                        logging.info("验证码检测到: %s", val)
                        return
            if time.time() - start_time > self.MAX_CODE_WAIT:
                raise TimeoutException("等待验证码超时")
            time.sleep(1)

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
        time.sleep(2)
        current_url = self.driver.current_url
        logging.info("Redirected to %s", current_url)
        if any(k in current_url.lower() for k in ("success", "dashboard", "home", "welcome")):
            return {"status": "success", "message": "注册成功", "url": current_url}
        try:
            toast = self.driver.find_element(By.CSS_SELECTOR, "div.el-message").text.strip()
            status = "error" if toast else "unknown"
            msg = toast or "无法确定注册结果"
        except Exception:
            status, msg = "unknown", "无法确定注册结果"
        return {"status": status, "message": msg, "url": current_url}


if __name__ == "__main__":
    tester = FastRegistrationTester(headless=False)
    print("RESULT:", tester.run())
