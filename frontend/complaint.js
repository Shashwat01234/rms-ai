document.addEventListener("DOMContentLoaded", () => {
    const name = localStorage.getItem("student_name") || "Student";
    document.getElementById("student_name").innerText = name;
});

document.getElementById("submitBtn").addEventListener("click", async () => {
    const query = document.getElementById("query").value.trim();
    const student_id = localStorage.getItem("student_id");

    if (!query) {
        alert("Please describe your issue.");
        return;
    }

    if (!student_id) {
        alert("Session expired. Please login again.");
        window.location.href = "login.html";
        return;
    }

    try {
        const response = await fetch("/submit_request", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id,
                query
            })
        });

        const data = await response.json();
        console.log("Response:", data);

        if (data.request_id) {
            alert(`
Request Submitted Successfully!

Request ID: ${data.request_id}
Assigned Technician: ${data.technician || "No technician available"}
Status: ${data.status}
            `);

            document.getElementById("query").value = "";
        } else {
            alert("Failed to submit request.");
        }

    } catch (err) {
        console.error(err);
        alert("Server error. Try again.");
    }
});
