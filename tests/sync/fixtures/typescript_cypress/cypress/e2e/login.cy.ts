describe('login', () => {
  it('valid login reaches secure area', () => {
    cy.visit('https://example.test/login');
    cy.get('#username').type('demo_user');
    cy.get('#password').type('demo_password');
    cy.get('#login').click();
    cy.contains('Secure Area');
  });

  it('invalid password shows error', () => {
    cy.visit('https://example.test/login');
    cy.get('#username').type('demo_user');
    cy.get('#password').type('wrong_password');
    cy.get('#login').click();
    cy.get('.error').should('be.visible');
  });
});
