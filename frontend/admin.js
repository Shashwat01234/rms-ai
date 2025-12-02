document.addEventListener("DOMContentLoaded", loadRequests);

async function loadRequests() {
    try {
        const res = await fetch("/admin/get_all_requests");
        const data = await res.json();

        const table = document.getElementById("requestTable");
        table.innerHTML = "";

        if (!data.length) {
            table.innerHTML = "<tr><td colspan='8'>No records found.</td></tr>";
            return;
        }

        data.forEach(r => {
            const tr = document.createElement("tr");

            tr.innerHTML = `
                <td>${r.request_id}</td>
                <td>${r.student_id}</td>
                <td>${r.query}</td>
                <td>${r.category}</td>
                <td>${r.technician || "N/A"}</td>
                <td>${r.assigned_time || "N/A"}</td>

                <td>
                    <span style="font-weight:bold; color:${
                        r.status === "resolved" ? "green" :
                        r.status === "pending" ? "orange" : "red"
                    };">
                        ${r.status}
                    </span>
                </td>

                <td>
                    <select id="status-${r.request_id}">
                        <option value="pending" ${r.status === "pending" ? "selected" : ""}>Pending</option>
                        <option value="resolved" ${r.status === "resolved" ? "selected" : ""}>Resolved</option>
                        <option value="no_technician" ${r.status === "no_technician" ? "selected" : ""}>No Technician</option>
                    </select>

                    <button onclick="updateStatus('${r.request_id}')">Update</button>
                </td>
            `;

            table.appendChild(tr);
        });

    } catch (err) {
        console.error(err);
        alert("Failed to load requests.");
    }
}

async function updateStatus(req_id) {
    const new_status = document.getElementById(`status-${req_id}`).value;

    try {
        const res = await fetch("/admin/update_status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ request_id: req_id, status: new_status })
        });

        const data = await res.json();

        alert("Status updated");
        loadRequests();

    } catch (err) {
        console.error(err);
        alert("Error updating status.");
    }
}
