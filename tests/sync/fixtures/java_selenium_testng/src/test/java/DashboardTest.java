package com.example.automation;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.testng.annotations.Test;
import org.testng.annotations.BeforeMethod;

public class DashboardTest {
    private WebDriver driver;

    @BeforeMethod
    public void setUp() {
        driver = new ChromeDriver();
    }

    @Test(groups = {"regression"})
    public void dashboardShowsWelcomeMessage() {
        driver.get("https://example.test/dashboard");
    }
}
