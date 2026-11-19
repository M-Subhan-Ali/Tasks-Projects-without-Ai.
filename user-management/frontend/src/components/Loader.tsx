interface LoaderProps {
    message: string;
}

function Loader({ message }: LoaderProps) {
    return (
        <div className="loader">
            <div className="spinner"></div>
            <p>{message}</p>
        </div>
    );
}

export default Loader;
