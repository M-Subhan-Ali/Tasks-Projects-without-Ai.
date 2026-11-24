import { useEffect, useRef, useState } from "react";

import { getErrorMessage } from "../services/apiClient";
import {
    createUser,
    deleteUser,
    getUsers,
    updateUser,
} from "../services/userService";
import type { LoadStatus, User, UserFormData } from "../types/user";

const PAGE_SIZE = 5;
const SEARCH_DELAY_MS = 300;

function useUsers() {
    const [users, setUsers] = useState<User[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);

    // searchInput updates on every keystroke (what the input shows);
    // search updates only after typing pauses (what we send to the server).
    const [searchInput, setSearchInput] = useState("");
    const [search, setSearch] = useState("");
    const searchTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

    const [loadStatus, setLoadStatus] = useState<LoadStatus>("loading");
    const [errorMessage, setErrorMessage] = useState("");
    const [reloadCount, setReloadCount] = useState(0);

    useEffect(() => {
        // Ignore a response that arrives after a newer request was started,
        // so slow old results never overwrite fresh ones.
        let isStale = false;

        getUsers({ search, page, limit: PAGE_SIZE })
            .then((data) => {
                if (isStale) {
                    return;
                }

                // The last row of the last page was deleted: step back a page.
                if (data.items.length === 0 && page > 1) {
                    setPage(page - 1);
                    return;
                }

                setUsers(data.items);
                setTotal(data.total);
                setLoadStatus("success");
            })
            .catch((error: unknown) => {
                if (isStale) {
                    return;
                }

                setErrorMessage(getErrorMessage(error));
                setLoadStatus("error");
            });

        return () => {
            isStale = true;
        };
    }, [search, page, reloadCount]);

    useEffect(() => () => clearTimeout(searchTimer.current), []);

    const reloadUsers = () => {
        setReloadCount((count) => count + 1);
    };

    const retryLoad = () => {
        setLoadStatus("loading");
        reloadUsers();
    };

    const changeSearch = (value: string) => {
        setSearchInput(value);

        clearTimeout(searchTimer.current);
        searchTimer.current = setTimeout(() => {
            setSearch(value.trim());
            setPage(1);
        }, SEARCH_DELAY_MS);
    };

    // After any change, reload the current page from the server: the server
    // decides ordering, totals and which users match the current search.
    const addUser = async (formData: UserFormData): Promise<void> => {
        await createUser(formData);
        reloadUsers();
    };

    const editUser = async (
        id: number,
        formData: UserFormData
    ): Promise<void> => {
        await updateUser(id, formData);
        reloadUsers();
    };

    const removeUser = async (id: number): Promise<void> => {
        await deleteUser(id);
        reloadUsers();
    };

    return {
        users,
        total,
        page,
        totalPages: Math.max(1, Math.ceil(total / PAGE_SIZE)),
        searchInput,
        isSearching: search !== "",
        loadStatus,
        errorMessage,
        retryLoad,
        changeSearch,
        setPage,
        addUser,
        editUser,
        removeUser,
    };
}

export default useUsers;
