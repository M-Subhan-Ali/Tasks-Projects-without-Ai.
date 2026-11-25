import { useState } from "react";

import AppHeader from "../components/AppHeader";
import Loader from "../components/Loader";
import UserForm from "../components/UserForm";
import UserTable from "../components/UserTable";
import useAuth from "../hooks/useAuth";
import useUsers from "../hooks/useUsers";
import { getErrorMessage } from "../services/apiClient";
import type { StatusMessage, User, UserFormData } from "../types/user";

function UsersPage() {
    const { account } = useAuth();
    // Hiding buttons is only for a nicer UI: the backend still returns 403
    // if a viewer calls POST/PUT/DELETE directly.
    const canEdit = account?.role === "admin";

    const {
        users,
        total,
        page,
        totalPages,
        searchInput,
        isSearching,
        loadStatus,
        errorMessage,
        retryLoad,
        changeSearch,
        setPage,
        addUser,
        editUser,
        removeUser,
    } = useUsers();

    const [isFormOpen, setIsFormOpen] = useState(false);
    const [selectedUser, setSelectedUser] = useState<User>();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [deletingUserId, setDeletingUserId] = useState<number>();
    const [message, setMessage] = useState<StatusMessage>();

    // Quick client-side hint only: it knows just the current page. The
    // backend's 409 is the real duplicate check.
    const existingEmails = users
        .filter((user) => user.id !== selectedUser?.id)
        .map((user) => user.email.toLowerCase());

    const handleAdd = () => {
        setSelectedUser(undefined);
        setMessage(undefined);
        setIsFormOpen(true);
    };

    const handleEdit = (user: User) => {
        setSelectedUser(user);
        setMessage(undefined);
        setIsFormOpen(true);
    };

    const handleCancel = () => {
        setSelectedUser(undefined);
        setIsFormOpen(false);
    };

    const handleSubmit = async (formData: UserFormData) => {
        setIsSubmitting(true);
        setMessage(undefined);

        try {
            if (selectedUser) {
                await editUser(selectedUser.id, formData);
                setMessage({ type: "success", text: "User updated successfully." });
            } else {
                await addUser(formData);
                setMessage({ type: "success", text: "User created successfully." });
            }

            handleCancel();
        } catch (error: unknown) {
            setMessage({ type: "error", text: getErrorMessage(error) });
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDelete = async (user: User) => {
        if (!window.confirm(`Are you sure you want to delete ${user.name}?`)) {
            return;
        }

        setDeletingUserId(user.id);
        setMessage(undefined);

        try {
            await removeUser(user.id);

            if (selectedUser?.id === user.id) {
                handleCancel();
            }

            setMessage({ type: "success", text: "User deleted successfully." });
        } catch (error: unknown) {
            setMessage({ type: "error", text: getErrorMessage(error) });
        } finally {
            setDeletingUserId(undefined);
        }
    };

    return (
        <div className="container">
            <AppHeader />

            <h1>User Management</h1>

            {loadStatus === "loading" && <Loader message="Loading users..." />}

            {loadStatus === "error" && (
                <div>
                    <p className="message error">{errorMessage}</p>

                    <button onClick={retryLoad}>Retry</button>
                </div>
            )}

            {loadStatus === "success" && (
                <>
                    {canEdit && (
                        <div className="toolbar">
                            <button className="btn-primary" onClick={handleAdd}>
                                Add User
                            </button>
                        </div>
                    )}

                    {message && (
                        <p className={`message ${message.type}`}>{message.text}</p>
                    )}

                    {canEdit && isFormOpen && (
                        <UserForm
                            key={selectedUser ? selectedUser.id : "new"}
                            user={selectedUser}
                            existingEmails={existingEmails}
                            isSubmitting={isSubmitting}
                            onSubmit={handleSubmit}
                            onCancel={handleCancel}
                        />
                    )}

                    <UserTable
                        users={users}
                        total={total}
                        page={page}
                        totalPages={totalPages}
                        searchInput={searchInput}
                        isSearching={isSearching}
                        onSearchChange={changeSearch}
                        onPageChange={setPage}
                        onEdit={handleEdit}
                        onDelete={handleDelete}
                        deletingUserId={deletingUserId}
                        canEdit={canEdit}
                    />
                </>
            )}
        </div>
    );
}

export default UsersPage;
