using NUnit.Framework;
using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;

namespace SampleAutomation
{
    [TestFixture]
    public class LoginTests
    {
        private IWebDriver driver;

        [SetUp]
        public void SetUp()
        {
            driver = new ChromeDriver();
        }

        [Test]
        public void ValidLoginReachesSecureArea()
        {
            driver.Navigate().GoToUrl("https://example.test/login");
            driver.FindElement(By.Id("username")).SendKeys("demo_user");
            driver.FindElement(By.Id("password")).SendKeys("demo_password");
            driver.FindElement(By.Id("login")).Click();
        }

        [TearDown]
        public void TearDown()
        {
            driver.Quit();
        }
    }
}
