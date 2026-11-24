import useAuth from "../hooks/useAuth";

function AppHeader() {
    const { account, logout } = useAuth();

    if (!account) {
        return null;
    }

    return (
        <header className="app-header">
            <span>
                Signed in as <strong>{account.email}</strong>{" "}
                <span className={`role-badge role-${account.role}`}>{account.role}</span>
            </span>

            <button onClick={() => void logout()}>Logout</button>
        </header>
    );
}

export default AppHeader;
