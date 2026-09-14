const validateField = () => {
    const content = document.getElementById("inspectionSummary").value;
    if (content.length <= 25) {
        alert("The inspection summary has to have more than 25 characters.");
        return false;
    }
    const checked = document.getElementById("terms").checked;
    if (!checked) {
        alert("You have to agree to the terms and conditions.");
        return false;
    }
    return true;
};
const form = document.getElementById("inspectionForm");
const updateForm = document.getElementById("updateForm");
const createCounter = () => {
    let count = 0;
    return () => {
        count++;
        return count;
    };
};
const counter = createCounter();
form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (validateField()) {
        const formData = {
            restaurantName: document.getElementById("restaurantName").value,
            restaurantAddress: document.getElementById("restaurantAddress").value,
            submitterEmail: document.getElementById("submitterEmail").value,
            inspectionSummary: document.getElementById("inspectionSummary").value,
            category: document.getElementById("category").value,
            terms: document.getElementById("terms").checked
        };
        fetch("/api/restaurants", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                restaurantName: formData.restaurantName,
                restaurantAddress: formData.restaurantAddress
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error("Failed to add restaurant.");
            }
            return response.json();
        })
        .then(() => {
            window.location.href = "/";
        })
        .catch(() => {
            showState("error");
        });
        const jsonString = JSON.stringify(formData);
        console.log(jsonString);
        const parsedObject = JSON.parse(jsonString);
        const {restaurantName, submitterEmail} = parsedObject;
        console.log(restaurantName);
        console.log(submitterEmail);
        const updatedParsedObject = {
            ...parsedObject,
            submissionDate: new Date().toISOString()
        };
        console.log(updatedParsedObject);
        const count = counter();
        console.log("The submission count is: ", count);
    }
});
updateForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const restaurantName = document.getElementById("updateRestaurantName").value;
    const restaurantAddress = document.getElementById("updateRestaurantAddress").value;
    fetch("/api/restaurants/1", {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            restaurantName: restaurantName,
            restaurantAddress: restaurantAddress
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Failed to update restaurant.");
        }
        return response.json();
    })
    .then(() => {
        window.location.href = "/";
    })
    .catch(() => {
        showState("error");
    });
});
const deleteForm = document.getElementById("deleteForm");
deleteForm.addEventListener("submit", (event) => {
    event.preventDefault();
    fetch("/api/restaurants/highest", {
        method: "DELETE"
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Failed to delete restaurant.");
        }
        return response.json();
    })
    .then(() => {
        window.location.href = "/";
    })
    .catch(() => {
        showState("error");
    });
});
const searchForm = document.getElementById("searchForm");
searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = document.getElementById("searchInput").value;
    showState("loading");
    fetch(`/api/restaurants/search?query=${encodeURIComponent(query)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error("Failed to search restaurants.");
            }
            return response.json();
        })
        .then(restaurants => {
            const tableBody = document.getElementById("inspectionTableBody");
            tableBody.innerHTML = "";
            if (restaurants.length === 0) {
                showState("empty");
                return;
            }
            restaurants.forEach(restaurant => {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${restaurant.id}</td>
                    <td>${restaurant.restaurantName}</td>
                    <td>${restaurant.restaurantAddress}</td>
                `;
                tableBody.appendChild(row);
            });
            showState("list");
        })
        .catch(() => {
            showState("error");
        });
});
function showState(state) {
    const loadingState = document.getElementById("loadingState");
    const emptyState = document.getElementById("emptyState");
    const errorState = document.getElementById("errorState");
    const listState = document.getElementById("listState");
    loadingState.hidden = true;
    emptyState.hidden = true;
    errorState.hidden = true;
    listState.hidden = true;
    if (state === "loading") {
        loadingState.hidden = false;
    }
    else if (state === "empty") {
        emptyState.hidden = false;
    }
    else if (state === "error") {
        errorState.hidden = false;
    }
    else if (state === "list") {
        listState.hidden = false;
    }
}
function loadRestaurants() {
    showState("loading");
    fetch("/api/restaurants")
        .then(response => {
            if (!response.ok) {
                throw new Error("Failed to load restaurants.");
            }
            return response.json();
        })
        .then(restaurants => {
            const tableBody = document.getElementById("inspectionTableBody");
            tableBody.innerHTML = "";
            if (restaurants.length === 0) {
                showState("empty");
                return;
            }
            restaurants.forEach(restaurant => {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${restaurant.id}</td>
                    <td>${restaurant.restaurantName}</td>
                    <td>${restaurant.restaurantAddress}</td>
                `;
                tableBody.appendChild(row);
            });
            showState("list");
        })
        .catch(() => {
            showState("error");
        });
}
loadRestaurants();