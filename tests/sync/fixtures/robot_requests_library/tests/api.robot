*** Settings ***
Library    RequestsLibrary

*** Variables ***
${BASE_URL}    https://example.test

*** Test Cases ***
Get Users Returns Ok
    Create Session    api    ${BASE_URL}
    ${response}=    GET On Session    api    /users
    Should Be Equal As Integers    ${response.status_code}    200
