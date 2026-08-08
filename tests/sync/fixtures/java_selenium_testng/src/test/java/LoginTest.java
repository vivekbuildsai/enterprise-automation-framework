package com.example.automation;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.By;
import org.testng.annotations.Test;
import org.testng.annotations.BeforeMethod;

public class LoginTest {
    private WebDriver driver;

    @BeforeMethod
    public void setUp() {
        driver = new ChromeDriver();
    }

    @Test(priority = 1, groups = {"smoke", "ui"})
    public void validLoginReachesSecureArea() {
        driver.get("https://example.test/login");
        driver.findElement(By.id("username")).sendKeys("demo_user");
        driver.findElement(By.id("password")).sendKeys("demo_password");
        driver.findElement(By.id("login")).click();
    }

    @Test(groups = {"regression", "ui"})
    public void invalidPasswordShowsError() {
        driver.get("https://example.test/login");
        driver.findElement(By.id("username")).sendKeys("demo_user");
        driver.findElement(By.id("password")).sendKeys("wrong_password");
        driver.findElement(By.id("login")).click();
    }
}
