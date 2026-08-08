"""A tiny, deliberately old-style Page Object — sample fixture data for
Example C (Framework Sync), not part of the framework itself. Represents
the kind of pre-existing Selenium+pytest automation repository an
engineer might ask this framework to analyze.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By


class LoginPage:
    def __init__(self, driver: "webdriver.Chrome") -> None:
        self.driver = driver

    def login(self, username: str, password: str) -> None:
        self.driver.find_element(By.ID, "username").send_keys(username)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
