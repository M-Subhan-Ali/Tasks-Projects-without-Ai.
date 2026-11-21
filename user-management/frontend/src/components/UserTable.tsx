import { useState } from "react";

import type { User } from "../types/user";
import Pagination from "./Pagination";
import SearchInput from "./SearchInput";

interface UserTableProps {
    users: User[];
    onEdit: (user: User) => void;
    onDelete: (user: User) => void;
    deletingUserId?: number;
    recordsPerPage?: number;
}

function UserTable({
    users,
    onEdit,
    onDelete,
    deletingUserId,
    recordsPerPage = 5,
}: UserTableProps) {
    const [search, setSearch] = useState("");
    const [currentPage, setCurrentPage] = useState(1);

    const searchValue = search.trim().toLowerCase();

    const filteredUsers = users.filter(
        (user) =>
            user.name.toLowerCase().includes(searchValue) ||
            user.email.toLowerCase().includes(searchValue)
    );

    const totalPages = Math.ceil(filteredUsers.length / recordsPerPage);

    // Keep the page in range when rows are removed (e.g. deleting the last
    // user on the last page).
    const page = Math.min(currentPage, Math.max(totalPages, 1));

    const startIndex = (page - 1) * recordsPerPage;

    const currentUsers = filteredUsers.slice(
        startIndex,
        startIndex + recordsPerPage
    );

    return (
        <div>
            <h2>User List</h2>

            <SearchInput
                value={search}
                placeholder="Search by name or email..."
                onChange={(value) => {
                    setSearch(value);
                    setCurrentPage(1);
                }}
            />

            <p>Total Records: {filteredUsers.length}</p>

            {filteredUsers.length === 0 ? (
                <p>No matching users found.</p>
            ) : (
                <>
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Email</th>
                                <th>Phone</th>
                                <th>City</th>
                                <th>Company</th>
                                <th>Actions</th>
                            </tr>
                        </thead>

                        <tbody>
                            {currentUsers.map((user) => (
                                <tr key={user.id}>
                                    <td>{user.name}</td>
                                    <td>{user.email}</td>
                                    <td>{user.phone}</td>
                                    <td>{user.city}</td>
                                    <td>{user.company.name}</td>
                                    <td>
                                        <button
                                            onClick={() => onEdit(user)}
                                            disabled={deletingUserId === user.id}
                                        >
                                            Edit
                                        </button>

                                        <button
                                            onClick={() => onDelete(user)}
                                            disabled={deletingUserId === user.id}
                                        >
                                            {deletingUserId === user.id
                                                ? "Deleting..."
                                                : "Delete"}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    <Pagination
                        currentPage={page}
                        totalPages={totalPages}
                        onPageChange={setCurrentPage}
                    />
                </>
            )}
        </div>
    );
}

export default UserTable;
