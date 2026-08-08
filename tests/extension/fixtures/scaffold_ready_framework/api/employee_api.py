class EmployeeApi:
    """Shared API client the new UI is expected to reuse rather than
    duplicate.
    """

    def get_employee(self, employee_id):
        response = self._client.get(f"/employees/{employee_id}")
        return response.json()
