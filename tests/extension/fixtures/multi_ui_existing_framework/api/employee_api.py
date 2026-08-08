class EmployeeApi:
    """Shared API client used by both the Support Portal and the Admin
    Portal — this is the capability a brand-new, zero-test third UI is
    expected to reuse rather than duplicate.
    """

    def get_employee(self, employee_id):
        response = self._client.get(f"/employees/{employee_id}")
        return response.json()

    def search(self, name):
        response = self._client.get("/employees/search")
        return response.json()
