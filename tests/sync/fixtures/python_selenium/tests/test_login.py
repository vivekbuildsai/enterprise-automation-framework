import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By


class LoginTest(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = webdriver.Chrome()

    def test_valid_login_reaches_secure_area(self) -> None:
        self.driver.get("https://example.test/login")
        self.driver.find_element(By.ID, "username").send_keys("demo_user")
        self.driver.find_element(By.ID, "password").send_keys("demo_password")
        self.driver.find_element(By.ID, "login").click()

    def tearDown(self) -> None:
        self.driver.quit()
