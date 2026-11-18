import { useState } from "react";

import type { Column } from "../../types/table";
import SearchInput from "./SearchInput";
import Pagination from "./Pagination";

interface DataTableProps<T> {
    title: string;
    data: T[];
    columns: Column<T>[];
    searchKeys: (keyof T)[];
    searchPlaceholder: string;
    getRowKey: (row: T) => number;
    onEdit: (row: T) => void;
    recordsPerPage?: number;
}

function DataTable<T>({
    title,
    data,
    columns,
    searchKeys,
    searchPlaceholder,
    getRowKey,
    onEdit,
    recordsPerPage = 5,
}: DataTableProps<T>) {
    const [search, setSearch] = useState("");
    const [currentPage, setCurrentPage] = useState(1);

    const searchValue = search.trim().toLowerCase();

    const filteredRows = data.filter((row) =>
        searchKeys.some((key) =>
            String(row[key]).toLowerCase().includes(searchValue)
        )
    );

    const totalPages = Math.ceil(filteredRows.length / recordsPerPage);

    const startIndex = (currentPage - 1) * recordsPerPage;

    const currentRows = filteredRows.slice(
        startIndex,
        startIndex + recordsPerPage
    );

    return (
        <div>
            <h2>{title}</h2>

            <SearchInput
                value={search}
                placeholder={searchPlaceholder}
                onChange={(value) => {
                    setSearch(value);
                    setCurrentPage(1);
                }}
            />

            <p>Total Records: {filteredRows.length}</p>

            {filteredRows.length === 0 ? (
                <p>No matching records found.</p>
            ) : (
                <>
                    <table>
                        <thead>
                            <tr>
                                {columns.map((column) => (
                                    <th key={String(column.key)}>
                                        {column.label}
                                    </th>
                                ))}
                                <th>Actions</th>
                            </tr>
                        </thead>

                        <tbody>
                            {currentRows.map((row) => (
                                <tr key={getRowKey(row)}>
                                    {columns.map((column) => (
                                        <td key={String(column.key)}>
                                            {String(row[column.key])}
                                        </td>
                                    ))}

                                    <td>
                                        <button onClick={() => onEdit(row)}>
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

export default DataTable;
