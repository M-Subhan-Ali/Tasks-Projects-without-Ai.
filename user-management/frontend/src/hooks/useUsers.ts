import { useEffect, useState } from "react";

import {
    createUser,
    deleteUser,
    getErrorMessage,
    getUsers,
    updateUser,
} from "../services/userService";
import type { LoadStatus, User, UserFormData } from "../types/user";

function useUsers() {
    const [users, setUsers] = useState<User[]>([]);
    const [loadStatus, setLoadStatus] = useState<LoadStatus>("loading");
    const [errorMessage, setErrorMessage] = useState("");

    useEffect(() => {
        if (loadStatus !== "loading") {
            return;
        }

        getUsers()
            .then((data) => {
                setUsers(data);
                setLoadStatus("success");
            })
            .catch((error: unknown) => {
                setErrorMessage(getErrorMessage(error));
                setLoadStatus("error");
            });
    }, [loadStatus]);

    const reloadUsers = () => {
        setLoadStatus("loading");
    };

    const addUser = async (formData: UserFormData): Promise<void> => {
        const createdUser = await createUser(formData);

        setUsers((prev) => [...prev, createdUser]);
    };

    const editUser = async (
        id: number,
        formData: UserFormData
    ): Promise<void> => {
        const updatedUser = await updateUser(id, formData);

        setUsers((prev) =>
            prev.map((user) => (user.id === id ? updatedUser : user))
        );
    };

    const removeUser = async (id: number): Promise<void> => {
        await deleteUser(id);

        setUsers((prev) => prev.filter((user) => user.id !== id));
    };

    return {
        users,
        loadStatus,
        errorMessage,
        reloadUsers,
        addUser,
        editUser,
        removeUser,
    };
}

export default useUsers;
