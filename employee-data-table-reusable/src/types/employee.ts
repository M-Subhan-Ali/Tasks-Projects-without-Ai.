export type EmployeeStatus = "Active" | "Inactive";

export interface Employee {
    id: number;
    name: string;
    email: string;
    department: string;
    designation: string;
    status: EmployeeStatus;
}

export type EmployeeFormData = Omit<Employee, "id">;

export type LoadStatus = "loading" | "success" | "error";
