import { useEffect, useState } from "react";

import {
    createUser,
    getErrorMessage,
    getUsers,
    toPayload,
    updateUser,
} from "../services/userService";
import { getSavedUsers, saveUsers } from "../services/userStorage";
import type { LoadStatus, User, UserFormData } from "../types/user";

function useUsers() {
    const [users, setUsers] = useState<User[]>(getSavedUsers);
    const [loadStatus, setLoadStatus] = useState<LoadStatus>(
        users.length > 0 ? "success" : "loading"
    );
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

    useEffect(() => {
        if (users.length > 0) {
            saveUsers(users);
        }
    }, [users]);

    const reloadUsers = () => {
        setLoadStatus("loading");
    };

    const addUser = async (formData: UserFormData): Promise<void> => {
        const createdUser = await createUser(formData);

        setUsers((prev) => [
            ...prev,
            {
                ...createdUser,
                id:
                    prev.length > 0
                        ? Math.max(...prev.map((user) => user.id)) + 1
                        : 1,
                isLocal: true,
            },
        ]);
    };

    const editUser = async (
        selectedUser: User,
        formData: UserFormData
    ): Promise<void> => {
        let updatedUser: User;

        if (selectedUser.isLocal) {
            updatedUser = {
                ...toPayload(formData),
                id: selectedUser.id,
                isLocal: true,
            };
        } else {
            updatedUser = await updateUser(selectedUser.id, formData);
        }

        setUsers((prev) =>
            prev.map((user) =>
                user.id === selectedUser.id ? updatedUser : user
            )
        );
    };

    return {
        users,
        loadStatus,
        errorMessage,
        reloadUsers,
        addUser,
        editUser,
    };
}

export default useUsers;
