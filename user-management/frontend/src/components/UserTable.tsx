import type { User } from "../types/user";
import Pagination from "./Pagination";
import SearchInput from "./SearchInput";

interface UserTableProps {
    users: User[];
    total: number;
    page: number;
    totalPages: number;
    searchInput: string;
    isSearching: boolean;
    onSearchChange: (value: string) => void;
    onPageChange: (page: number) => void;
    onEdit: (user: User) => void;
    onDelete: (user: User) => void;
    deletingUserId?: number;
}

// Presentational only: searching and paging happen on the server (see useUsers).
function UserTable({
    users,
    total,
    page,
    totalPages,
    searchInput,
    isSearching,
    onSearchChange,
    onPageChange,
    onEdit,
    onDelete,
    deletingUserId,
}: UserTableProps) {
    return (
        <div>
            <h2>User List</h2>

            <SearchInput
                value={searchInput}
                placeholder="Search by name or email..."
                onChange={onSearchChange}
            />

            <p>Total Records: {total}</p>

            {users.length === 0 ? (
                <p>
                    {isSearching
                        ? "No matching users found."
                        : 'No users found. Click "Add User" to create one.'}
                </p>
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
                            {users.map((user) => (
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
                        onPageChange={onPageChange}
                    />
                </>
            )}
        </div>
    );
}

export default UserTable;
