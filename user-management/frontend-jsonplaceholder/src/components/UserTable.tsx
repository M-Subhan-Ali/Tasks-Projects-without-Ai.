import { useState } from "react";

import type { User } from "../types/user";
import Pagination from "./Pagination";
import SearchInput from "./SearchInput";

interface UserTableProps {
    users: User[];
    onEdit: (user: User) => void;
    recordsPerPage?: number;
}

function UserTable({ users, onEdit, recordsPerPage = 5 }: UserTableProps) {
    const [search, setSearch] = useState("");
    const [currentPage, setCurrentPage] = useState(1);

    const searchValue = search.trim().toLowerCase();

    const filteredUsers = users.filter(
        (user) =>
            user.name.toLowerCase().includes(searchValue) ||
            user.email.toLowerCase().includes(searchValue)
    );

    const totalPages = Math.ceil(filteredUsers.length / recordsPerPage);

    const startIndex = (currentPage - 1) * recordsPerPage;

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
                                    <td>{user.company.name}</td>
                                    <td>
                                        <button onClick={() => onEdit(user)}>
                                            Edit
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    <Pagination
                        currentPage={currentPage}
                        totalPages={totalPages}
                        onPageChange={setCurrentPage}
                    />
                </>
            )}
        </div>
    );
}

export default UserTable;
