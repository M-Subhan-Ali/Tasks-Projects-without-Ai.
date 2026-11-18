import { useEffect, useState } from "react";
import type { SubmitEvent } from "react";

import type {
    Employee,
    EmployeeFormData,
} from "../../types/employee";

interface EmployeeFormProps {
    employee?: Employee;
    onSubmit: (employee: EmployeeFormData) => void;
    onCancel: () => void;
}

const initialFormData: EmployeeFormData = {
    name: "",
    email: "",
    department: "",
    designation: "",
    status: "Active",
};

function EmployeeForm({
    employee,
    onSubmit,
    onCancel,
}: EmployeeFormProps) {

    const [formData, setFormData] =
        useState<EmployeeFormData>(initialFormData);

    const [errors, setErrors] = useState<
        Partial<Record<keyof EmployeeFormData, string>>
    >({});

    useEffect(() => {
        if (employee) {
            setFormData({
                name: employee.name,
                email: employee.email,
                department: employee.department,
                designation: employee.designation,
                status: employee.status,
            });
        } else {
            setFormData({ ...initialFormData });
        }

        setErrors({});
    }, [employee]);

    const handleChange = (
        field: keyof EmployeeFormData,
        value: string
    ) => {
        setFormData((prev) => ({
            ...prev,
            [field]: value,
        }));
    };

    const validateForm = () => {
        const newErrors: Partial<
            Record<keyof EmployeeFormData, string>
        > = {};

        if (!formData.name.trim()) {
            newErrors.name = "Name is required";
        }

        if (!formData.email.trim()) {
            newErrors.email = "Email is required";
        } else if (
            !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)
        ) {
            newErrors.email = "Please enter a valid email";
        }

        if (!formData.department.trim()) {
            newErrors.department = "Department is required";
        }

        setErrors(newErrors);

        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (!validateForm()) {
            return;
        }

        onSubmit({
            ...formData,
            name: formData.name.trim(),
            email: formData.email.trim(),
            department: formData.department.trim(),
            designation: formData.designation.trim(),
        });
    };

    return (
        <form onSubmit={handleSubmit}>
            <h2>{employee ? "Edit Employee" : "Add Employee"}</h2>

            <div>
                <label>Name</label>

                <input
                    type="text"
                    placeholder="Enter employee name"
                    value={formData.name}
                    onChange={(e) => handleChange("name", e.target.value)}
                />

                {errors.name && <p>{errors.name}</p>}
            </div>

            <div>
                <label>Email</label>

                <input
                    type="email"
                    placeholder="Enter employee email"
                    value={formData.email}
                    onChange={(e) => handleChange("email", e.target.value)}
                />

                {errors.email && <p>{errors.email}</p>}
            </div>

            <div>
                <label>Department</label>

                <input
                    type="text"
                    placeholder="Enter department"
                    value={formData.department}
                    onChange={(e) =>
                        handleChange("department", e.target.value)
                    }
                />

                {errors.department && <p>{errors.department}</p>}
            </div>

            <div>
                <label>Designation</label>

                <input
                    type="text"
                    placeholder="Enter designation"
                    value={formData.designation}
                    onChange={(e) =>
                        handleChange("designation", e.target.value)
                    }
                />
            </div>

            <div>
                <label>Status</label>

                <select
                    value={formData.status}
                    onChange={(e) =>
                        handleChange("status", e.target.value)
                    }
                >
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                </select>
            </div>

            <div>
                <button type="submit">
                    {employee ? "Update Employee" : "Add Employee"}
                </button>

                <button type="button" onClick={onCancel}>
                    Cancel
                </button>
            </div>
        </form>
    );
}

export default EmployeeForm;
