import { useEffect, useState } from "react";
import api from "../services/api";

function Home({ user }) {
  const [records, setRecords] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) {
      return;
    }

    const fetchRecords = async () => {
      try {
        const response = await api.get("/records");
        setRecords(response.data);
      } catch {
        setError("Unable to load records.");
      }
    };

    fetchRecords();
  }, [user]);

  if (!user) {
    return (
      <div>
        <h1>Local Restaurant Inspections</h1>
        <p>Login required</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Local Restaurant Inspections</h1>

      {error && <p>{error}</p>}

      {records.length === 0 ? (
        <p>No records found.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Restaurant Name</th>
              <th>Restaurant Address</th>
            </tr>
          </thead>

          <tbody>
            {records.map((record) => (
              <tr key={record.id}>
                <td>{record.id}</td>
                <td>{record.restaurant_name}</td>
                <td>{record.restaurant_address}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default Home;