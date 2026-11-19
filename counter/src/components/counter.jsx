import { useState } from "react";

function Counter() {
    const [count, setCount] = useState(0)
    console.log(count)
    return (<div className="counter">
        <h1>Counter Counts</h1>
        <h3>{count}</h3>
        <div className="center">
            <button onClick={() => setCount(Math.max(0, count - 1))}>
                decrement
            </button>
            <button onClick={() => setCount((prev) => prev + 1)}>
                Counter
            </button>
            <button onClick={() => setCount(0)}>
                reset
            </button>
        </div>
    </div>)
}
export default Counter;