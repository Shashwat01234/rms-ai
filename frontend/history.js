document.addEventListener("DOMContentLoaded", () => {
    const student_id = localStorage.getItem("student_id");

    if (!student_id) {
        alert("Session expired. Please login again.");
        window.location.href = "login.html";
        return;
    }

    loadHistory(student_id);
});

async function loadHistory(student_id) {
    try {
        const res = await fetch(`/api/history/${student_id}`);
        const data = await res.json();

        const container = document.getElementById("historyList");
        container.innerHTML = "";

        if (!data || data.length === 0) {
            container.innerHTML = "<p>No complaint history found.</p>";
            return;
        }

        data.forEach(rec => {
            const div = document.createElement("div");
            div.className = "record";

            const statusClass =
                rec.status === "resolved"
                    ? "resolved"
                    : rec.status === "no_technician"
                        ? "no_technician"
                        : "pending";

            div.innerHTML = `
                <p><b>Request ID:</b> ${rec.request_id}</p>
                <p><b>Issue:</b> ${rec.query}</p>
                <p><b>Category:</b> ${rec.category}</p>
                <p><b>Technician:</b> ${rec.technician || "Not assigned"}</p>
                <p><b>Assigned Time:</b> ${rec.assigned_time || "N/A"}</p>
                <p><b>Your Free Time:</b> ${rec.student_free_time || "N/A"}</p>
                <p><b>Status:</b> <span class="status ${statusClass}">${rec.status}</span></p>
            `;

            container.appendChild(div);
        });

    } catch (error) {
        console.error(error);
        document.getElementById("historyList").innerHTML =
            "<p>Error loading history. Try again.</p>";
    }
}
