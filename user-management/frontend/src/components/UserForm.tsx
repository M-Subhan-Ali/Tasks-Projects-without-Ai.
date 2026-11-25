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
    city: "",
    company: "",
};

const NAME_PATTERN = /^[A-Za-z\s.'-]+$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_PATTERN = /^\+?[0-9\s()-]+$/;
const PHONE_DISALLOWED_CHARS = /[^0-9\s()+-]/g;

function getInitialFormData(user?: User): UserFormData {
    if (!user) {
        return initialFormData;
    }

    return {
        name: user.name,
        email: user.email,
        phone: user.phone,
        city: user.city ?? "",
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

        const name = formData.name.trim();
        const email = formData.email.trim();
        const phone = formData.phone.trim();
        const city = formData.city.trim();
        const company = formData.company.trim();
        const phoneDigits = phone.replace(/\D/g, "");

        if (!name) {
            newErrors.name = "Name is required";
        } else if (name.length < 2) {
            newErrors.name = "Name must be at least 2 characters";
        } else if (!NAME_PATTERN.test(name)) {
            newErrors.name = "Name can only contain letters, spaces, . ' -";
        }

        if (!email) {
            newErrors.email = "Email is required";
        } else if (!EMAIL_PATTERN.test(email)) {
            newErrors.email = "Please enter a valid email";
        } else if (existingEmails.includes(email.toLowerCase())) {
            newErrors.email = "This email already exists";
        }

        if (!phone) {
            newErrors.phone = "Phone number is required";
        } else if (!PHONE_PATTERN.test(phone)) {
            newErrors.phone = "Phone number can only contain digits, spaces, + - ( )";
        } else if (phoneDigits.length < 7 || phoneDigits.length > 15) {
            newErrors.phone = "Phone number must have 7 to 15 digits";
        }

        // City is optional: only validate it when something was typed.
        if (city && city.length < 2) {
            newErrors.city = "City must be at least 2 characters";
        } else if (city && !NAME_PATTERN.test(city)) {
            newErrors.city = "City can only contain letters, spaces, . ' -";
        }

        if (!company) {
            newErrors.company = "Company name is required";
        } else if (company.length < 2) {
            newErrors.company = "Company name must be at least 2 characters";
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
            city: formData.city.trim(),
            company: formData.company.trim(),
        });
    };

    return (
        <form className="card" onSubmit={handleSubmit} noValidate>
            <h2>{user ? "Edit User" : "Add User"}</h2>

            <div>
                <label>Name</label>

                <input
                    type="text"
                    placeholder="Enter name"
                    maxLength={100}
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
                    maxLength={100}
                    value={formData.email}
                    onChange={(e) => handleChange("email", e.target.value)}
                />

                {errors.email && <span className="error-text">{errors.email}</span>}
            </div>

            <div>
                <label>Phone</label>

                <input
                    type="tel"
                    inputMode="tel"
                    placeholder="e.g. 0300-1234567"
                    maxLength={20}
                    value={formData.phone}
                    onChange={(e) =>
                        handleChange(
                            "phone",
                            e.target.value.replace(PHONE_DISALLOWED_CHARS, "")
                        )
                    }
                />

                {errors.phone && <span className="error-text">{errors.phone}</span>}
            </div>

            <div>
                <label>City (optional)</label>

                <input
                    type="text"
                    placeholder="Enter city"
                    maxLength={100}
                    value={formData.city}
                    onChange={(e) => handleChange("city", e.target.value)}
                />

                {errors.city && <span className="error-text">{errors.city}</span>}
            </div>

            <div>
                <label>Company</label>

                <input
                    type="text"
                    placeholder="Enter company name"
                    maxLength={100}
                    value={formData.company}
                    onChange={(e) => handleChange("company", e.target.value)}
                />

                {errors.company && (
                    <span className="error-text">{errors.company}</span>
                )}
            </div>

            <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={isSubmitting}>
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
