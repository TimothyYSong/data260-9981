import { useState } from "react";
import { useNavigate } from "react-router-dom";

function DeleteRecord({ user, deleteRecord }) {
  const [recordId, setRecordId] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  if (!user) {
    return <p>Login required</p>;
  }

  const handleDelete = async (event) => {
    event.preventDefault();
    setError("");

    try {
      await deleteRecord(recordId);
      navigate("/");
    } catch {
      setError("Unable to delete record.");
    }
  };

  return (
    <div>
      <h1>Delete Restaurant Inspection</h1>

      {error && <p>{error}</p>}

      <form onSubmit={handleDelete}>
        <div>
          <label htmlFor="recordId">Record ID</label>
          <input
            id="recordId"
            type="number"
            value={recordId}
            onChange={(event) => setRecordId(event.target.value)}
            required
          />
        </div>

        <button type="submit">Delete Inspection</button>
      </form>
    </div>
  );
}

export default DeleteRecord;