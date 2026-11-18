import type { Employee } from "../types/employee";

export const employees: Employee[] = [
    {
        id: 1,
        name: "John Smith",
        email: "john@example.com",
        department: "Engineering",
        designation: "Frontend Developer",
        status: "Active",
    },
    {
        id: 2,
        name: "Sarah Johnson",
        email: "sarah@example.com",
        department: "HR",
        designation: "HR Manager",
        status: "Active",
    },
    {
        id: 3,
        name: "David Brown",
        email: "david@example.com",
        department: "Design",
        designation: "UI Designer",
        status: "Inactive",
    },
    {
        id: 4,
        name: "Michael Wilson",
        email: "michael@example.com",
        department: "Engineering",
        designation: "Backend Developer",
        status: "Active",
    },
    {
        id: 5,
        name: "Emily Davis",
        email: "emily@example.com",
        department: "Marketing",
        designation: "Marketing Manager",
        status: "Active",
    },
    {
        id: 6,
        name: "James Taylor",
        email: "james@example.com",
        department: "Finance",
        designation: "Accountant",
        status: "Inactive",
    },
];

export function fetchEmployees(shouldFail: boolean): Promise<Employee[]> {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            if (shouldFail) {
                reject(new Error("Failed to load employees. Please try again."));
                return;
            }

            resolve(employees);
        }, 1000);
    });
}
