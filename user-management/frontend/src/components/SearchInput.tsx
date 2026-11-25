interface SearchInputProps {
    value: string;
    placeholder: string;
    onChange: (value: string) => void;
}

function SearchInput({ value, placeholder, onChange }: SearchInputProps) {
    return (
        <input
            type="text"
            className="search-input"
            placeholder={placeholder}
            value={value}
            onChange={(e) => onChange(e.target.value)}
        />
    );
}

export default SearchInput;
