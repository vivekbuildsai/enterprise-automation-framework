package com.example.automation;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.By;
import org.junit.Test;
import org.junit.Before;

public class LoginTest {
    private WebDriver driver;

    @Before
    public void setUp() {
        driver = new ChromeDriver();
    }

    @Test
    public void validLoginReachesSecureArea() {
        driver.get("https://example.test/login");
        driver.findElement(By.id("username")).sendKeys("demo_user");
        driver.findElement(By.id("login")).click();
    }

    @Test
    public void invalidPasswordShowsError() {
        driver.get("https://example.test/login");
        driver.findElement(By.id("username")).sendKeys("demo_user");
        driver.findElement(By.id("password")).sendKeys("wrong_password");
        driver.findElement(By.id("login")).click();
    }
}
