import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { createRecord } from "../features/recordsSlice";

function CreateRecord({ user }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const loading = useSelector((state) => state.records.loading);
  const reduxError = useSelector((state) => state.records.error);

  const [restaurantName, setRestaurantName] = useState("");
  const [restaurantAddress, setRestaurantAddress] = useState("");
  const [inspectionCode, setInspectionCode] = useState("");
  const [violationCount, setViolationCount] = useState(0);
  const [restaurantId, setRestaurantId] = useState("");

  if (!user) {
    return <p>Login required</p>;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();

    const resultAction = await dispatch(
      createRecord({
        restaurant_name: restaurantName,
        restaurant_address: restaurantAddress,
        inspection_code: inspectionCode,
        violation_count: Number(violationCount),
        restaurant_id: Number(restaurantId),
      })
    );

    if (createRecord.fulfilled.match(resultAction)) {
      navigate("/");
    }
  };

  return (
    <div>
      <h1>Add Restaurant Inspection</h1>

      {reduxError && <p>{reduxError}</p>}

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="restaurantName">Restaurant Name</label>
          <input
            id="restaurantName"
            type="text"
            value={restaurantName}
            onChange={(event) => setRestaurantName(event.target.value)}
            required
          />
        </div>

        <div>
          <label htmlFor="restaurantAddress">Restaurant Address</label>
          <input
            id="restaurantAddress"
            type="text"
            value={restaurantAddress}
            onChange={(event) => setRestaurantAddress(event.target.value)}
            required
          />
        </div>

        <div>
          <label htmlFor="inspectionCode">Inspection Code</label>
          <input
            id="inspectionCode"
            type="text"
            value={inspectionCode}
            onChange={(event) => setInspectionCode(event.target.value)}
            placeholder="INSP-20002"
            required
          />
        </div>

        <div>
          <label htmlFor="violationCount">Violation Count</label>
          <input
            id="violationCount"
            type="number"
            min="0"
            value={violationCount}
            onChange={(event) => setViolationCount(event.target.value)}
            required
          />
        </div>

        <div>
          <label htmlFor="restaurantId">Restaurant ID</label>
          <input
            id="restaurantId"
            type="number"
            min="1"
            value={restaurantId}
            onChange={(event) => setRestaurantId(event.target.value)}
            required
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? "Adding..." : "Add Inspection"}
        </button>
      </form>
    </div>
  );
}

export default CreateRecord;