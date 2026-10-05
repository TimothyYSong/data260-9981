import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  fetchRecords,
  deleteRecordAsync,
} from "../features/recordsSlice";

function Home({ user }) {
  const dispatch = useDispatch();

  const records = useSelector((state) => state.records.items);
  const loading = useSelector((state) => state.records.loading);
  const error = useSelector((state) => state.records.error);

  useEffect(() => {
    if (user && records.length === 0) {
      dispatch(fetchRecords());
    }
  }, [dispatch, user, records.length]);

  const handleDelete = async (id) => {
    await dispatch(deleteRecordAsync(id));
  };

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

      {loading && <p>Loading records...</p>}

      {error && <p>{error}</p>}

      {!loading && records.length === 0 ? (
        <p>No records found.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Restaurant Name</th>
              <th>Restaurant Address</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {records.map((record) => (
              <tr key={record.id}>
                <td>{record.id}</td>
                <td>{record.restaurant_name}</td>
                <td>{record.restaurant_address}</td>
                <td>
                  <button
                    type="button"
                    onClick={() => handleDelete(record.id)}
                    disabled={loading}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default Home;