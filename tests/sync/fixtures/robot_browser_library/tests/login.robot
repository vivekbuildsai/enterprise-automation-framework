*** Settings ***
Library    Browser
Test Setup    New Browser    chromium    headless=True

*** Variables ***
${URL}    https://example.test/login

*** Test Cases ***
Valid Login
    New Page    ${URL}
    Fill Text    id=username    demo_user
    Fill Text    id=password    demo_password
    Click    id=login
    Get Text    h2    contains    Secure Area
