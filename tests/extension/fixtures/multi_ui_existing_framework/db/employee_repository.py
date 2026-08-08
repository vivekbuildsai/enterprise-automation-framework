class EmployeeRepository:
    __tablename__ = "employee"

    def find_by_id(self, employee_id):
        query = "SELECT * FROM employee WHERE id = ?"
        return self.session.execute(query, [employee_id])
