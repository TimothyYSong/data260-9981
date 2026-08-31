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
const createCounter = () => {
    let count = 0;
    return () => {
        count++;
        return count;
    }
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