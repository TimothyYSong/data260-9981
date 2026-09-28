import { useState } from "react";
import { useNavigate } from "react-router-dom";

function CreateRecord({ user, addRecord }) {
  const [restaurantName, setRestaurantName] = useState("");
  const [restaurantAddress, setRestaurantAddress] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  if (!user) {
    return <p>Login required</p>;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    try {
      await addRecord({
        restaurant_name: restaurantName,
        restaurant_address: restaurantAddress,
      });

      navigate("/");
    } catch {
      setError("Unable to create record.");
    }
  };

  return (
    <div>
      <h1>Add Restaurant Inspection</h1>

      {error && <p>{error}</p>}

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

        <button type="submit">Add Inspection</button>
      </form>
    </div>
  );
}

export default CreateRecord;