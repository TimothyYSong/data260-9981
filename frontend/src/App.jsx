import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Login from "./components/Login";
import Home from "./pages/Home";
import CreateRecord from "./pages/CreateRecord";
import UpdateRecord from "./pages/UpdateRecord";
import DeleteRecord from "./pages/DeleteRecord";
import api from "./services/api";

function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const response = await api.get("/me");
        setUser(response.data);
      } catch {
        setUser(null);
      }
    };

    loadUser();
  }, []);

  const addRecord = async (record) => {
    await api.post("/records", record);
  };

  const updateRecord = async (id, record) => {
    await api.put(`/records/${id}`, record);
  };

  const deleteRecord = async (id) => {
    await api.delete(`/records/${id}`);
  };

  return (
    <BrowserRouter>
      <div>
       <nav>
        <Link to="/">Home</Link>{" "}
        {!user && <Link to="/login">Login</Link>}{" "}
        {user && <Link to="/create">Add Record</Link>}{" "}
        {user && <Link to="/update">Update Record</Link>}{" "}
        {user && <Link to="/delete">Delete Record</Link>}
      </nav>

        <Routes>
          <Route path="/" element={<Home user={user} />} />
          <Route path="/login" element={<Login onLogin={setUser} />} />
          <Route
            path="/create"
            element={<CreateRecord user={user} addRecord={addRecord} />}
          />
          <Route
            path="/update"
            element={<UpdateRecord user={user} updateRecord={updateRecord} />}
          />
          <Route
            path="/delete"
            element={<DeleteRecord user={user} deleteRecord={deleteRecord} />}
          />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;