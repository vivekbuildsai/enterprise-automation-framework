*** Settings ***
Library    SeleniumLibrary
Resource   ../resources/common.resource
Suite Setup    Open Browser To Login Page
Suite Teardown    Close All Browsers

*** Variables ***
${URL}         https://example.test/login
${BROWSER}     chrome

*** Test Cases ***
Valid Login
    [Documentation]    A registered user can log in with valid credentials.
    [Tags]    smoke
    Login As Standard User
    Page Should Contain    Dashboard

Invalid Login Shows Error
    [Documentation]    An invalid password shows an error message.
    [Tags]    regression
    Input Text      id=username    standard_user
    Input Text      id=password    wrong_password
    Click Button    id=login
    Page Should Contain    Invalid credentials
