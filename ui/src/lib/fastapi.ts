// lib/fastapi.ts

const BASE_URL = "localhost:8000"; // Change to your FastAPI URL

// GET /state
export async function getState() {
    const res = await fetch(`http://${BASE_URL}/state`, {
        cache: 'no-store'  // This is equivalent to getServerSideProps behavior
    });
    if (!res.ok) throw new Error("Failed to fetch state");
    return res.json();
}
