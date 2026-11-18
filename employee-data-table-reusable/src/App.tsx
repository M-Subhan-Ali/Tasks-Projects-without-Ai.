import { useCallback, useEffect, useState } from "react";

import DataTable from "./components/DataTable/DataTable";
import EmployeeForm from "./components/EmployeeForm/EmployeeForm";
import { fetchEmployees } from "./data/employees";
import type {
    Employee,
    EmployeeFormData,
    LoadStatus,
} from "./types/employee";
import type { Column } from "./types/table";

const employeeColumns: Column<Employee>[] = [
    { key: "name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "department", label: "Department" },
    { key: "designation", label: "Designation" },
    { key: "status", label: "Status" },
];

const employeeSearchKeys: (keyof Employee)[] = ["name", "email"];

function App() {
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [loadStatus, setLoadStatus] = useState<LoadStatus>("loading");
    const [errorMessage, setErrorMessage] = useState("");
    const [isFormOpen, setIsFormOpen] = useState(false);
    const [selectedEmployee, setSelectedEmployee] = useState<Employee>();

    const loadEmployees = useCallback((shouldFail: boolean) => {
        setLoadStatus("loading");
        setIsFormOpen(false);
        setSelectedEmployee(undefined);

        fetchEmployees(shouldFail)
            .then((data) => {
                setEmployees(data);
                setLoadStatus("success");
            })
            .catch((error: unknown) => {
                setErrorMessage(
                    error instanceof Error
                        ? error.message
                        : "Something went wrong."
                );
                setLoadStatus("error");
            });
    }, []);

    useEffect(() => {
        loadEmployees(false);
    }, [loadEmployees]);

    const handleAdd = () => {
        setSelectedEmployee(undefined);
        setIsFormOpen(true);
    };

    const handleEdit = (employee: Employee) => {
        setSelectedEmployee(employee);
        setIsFormOpen(true);
    };

    const handleCancel = () => {
        setSelectedEmployee(undefined);
        setIsFormOpen(false);
    };

    const handleSubmit = (formData: EmployeeFormData) => {
        if (selectedEmployee) {
            setEmployees((prev) =>
                prev.map((employee) =>
                    employee.id === selectedEmployee.id
                        ? { ...formData, id: selectedEmployee.id }
                        : employee
                )
            );
        } else {
            setEmployees((prev) => [
                ...prev,
                {
                    ...formData,
                    id:
                        prev.length > 0
                            ? Math.max(...prev.map((employee) => employee.id)) + 1
                            : 1,
                },
            ]);
        }

        handleCancel();
    };

    return (
        <div>
            <h1>Employee Data Table</h1>

            {loadStatus === "loading" && <p>Loading employees...</p>}

            {loadStatus === "error" && (
                <div>
                    <p>{errorMessage}</p>

                    <button onClick={() => loadEmployees(false)}>
                        Retry
                    </button>
                </div>
            )}

            {loadStatus === "success" && (
                <>
                    <div>
                        <button onClick={handleAdd}>Add Employee</button>

                        <button onClick={() => loadEmployees(true)}>
                            Simulate Error
                        </button>
                    </div>

                    {isFormOpen && (
                        <EmployeeForm
                            employee={selectedEmployee}
                            onSubmit={handleSubmit}
                            onCancel={handleCancel}
                        />
                    )}

                    {employees.length === 0 ? (
                        <p>No employees found. Click "Add Employee" to create one.</p>
                    ) : (
                        <DataTable
                            title="Employee List"
                            data={employees}
                            columns={employeeColumns}
                            searchKeys={employeeSearchKeys}
                            searchPlaceholder="Search by name or email..."
                            getRowKey={(employee) => employee.id}
                            onEdit={handleEdit}
                        />
                    )}
                </>
            )}
        </div>
    );
}

export default App;
