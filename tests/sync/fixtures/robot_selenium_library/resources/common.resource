*** Settings ***
Library    SeleniumLibrary

*** Keywords ***
Open Browser To Login Page
    Open Browser    ${URL}    ${BROWSER}

Login As Standard User
    Input Text      id=username    standard_user
    Input Text      id=password    standard_password
    Click Button    id=login
