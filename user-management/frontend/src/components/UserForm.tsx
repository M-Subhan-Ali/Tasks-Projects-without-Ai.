import { useState } from "react";
import type { SubmitEvent } from "react";

import type { FormErrors, User, UserFormData } from "../types/user";

interface UserFormProps {
    user?: User;
    existingEmails: string[];
    isSubmitting: boolean;
    onSubmit: (formData: UserFormData) => void;
    onCancel: () => void;
}

const initialFormData: UserFormData = {
    name: "",
    email: "",
    phone: "",
    company: "",
};

function getInitialFormData(user?: User): UserFormData {
    if (!user) {
        return initialFormData;
    }

    return {
        name: user.name,
        email: user.email,
        phone: user.phone,
        company: user.company.name,
    };
}

function UserForm({
    user,
    existingEmails,
    isSubmitting,
    onSubmit,
    onCancel,
}: UserFormProps) {
    const [formData, setFormData] = useState<UserFormData>(() =>
        getInitialFormData(user)
    );

    const [errors, setErrors] = useState<FormErrors>({});

    const handleChange = (field: keyof UserFormData, value: string) => {
        setFormData((prev) => ({
            ...prev,
            [field]: value,
        }));
    };

    const validateForm = () => {
        const newErrors: FormErrors = {};

        if (!formData.name.trim()) {
            newErrors.name = "Name is required";
        }

        if (!formData.email.trim()) {
            newErrors.email = "Email is required";
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
            newErrors.email = "Please enter a valid email";
        } else if (
            existingEmails.includes(formData.email.trim().toLowerCase())
        ) {
            newErrors.email = "This email already exists";
        }

        if (!formData.phone.trim()) {
            newErrors.phone = "Phone number is required";
        }

        if (!formData.company.trim()) {
            newErrors.company = "Company name is required";
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
            name: formData.name.trim(),
            email: formData.email.trim(),
            phone: formData.phone.trim(),
            company: formData.company.trim(),
        });
    };

    return (
        <form onSubmit={handleSubmit} noValidate>
            <h2>{user ? "Edit User" : "Add User"}</h2>

            <div>
                <label>Name</label>

                <input
                    type="text"
                    placeholder="Enter name"
                    value={formData.name}
                    onChange={(e) => handleChange("name", e.target.value)}
                />

                {errors.name && <span className="error-text">{errors.name}</span>}
            </div>

            <div>
                <label>Email</label>

                <input
                    type="email"
                    placeholder="Enter email"
                    value={formData.email}
                    onChange={(e) => handleChange("email", e.target.value)}
                />

                {errors.email && <span className="error-text">{errors.email}</span>}
            </div>

            <div>
                <label>Phone</label>

                <input
                    type="text"
                    placeholder="Enter phone number"
                    value={formData.phone}
                    onChange={(e) => handleChange("phone", e.target.value)}
                />

                {errors.phone && <span className="error-text">{errors.phone}</span>}
            </div>

            <div>
                <label>Company</label>

                <input
                    type="text"
                    placeholder="Enter company name"
                    value={formData.company}
                    onChange={(e) => handleChange("company", e.target.value)}
                />

                {errors.company && (
                    <span className="error-text">{errors.company}</span>
                )}
            </div>

            <div>
                <button type="submit" disabled={isSubmitting}>
                    {isSubmitting
                        ? "Saving..."
                        : user
                          ? "Update User"
                          : "Add User"}
                </button>

                <button type="button" onClick={onCancel} disabled={isSubmitting}>
                    Cancel
                </button>
            </div>
        </form>
    );
}

export default UserForm;
