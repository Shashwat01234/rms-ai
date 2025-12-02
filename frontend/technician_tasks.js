document.addEventListener("DOMContentLoaded", () => {
    const tech_name = localStorage.getItem("tech_name");

    if (!tech_name) {
        alert("Session expired. Please login again.");
        window.location.href = "technician_login.html";
        return;
    }

    loadTasks(tech_name);
});

async function loadTasks(name) {
    try {
        const res = await fetch(`/technician/get_tasks?name=${name}`);
        const tasks = await res.json();

        const list = document.getElementById("taskList");
        list.innerHTML = "";

        if (!tasks.length) {
            list.innerHTML = "<p>No tasks assigned.</p>";
            return;
        }

        tasks.forEach(t => {
            const div = document.createElement("div");
            div.className = "task";

            div.innerHTML = `
                <p><b>Request ID:</b> ${t.request_id}</p>
                <p><b>Issue:</b> ${t.query}</p>
                <p><b>Category:</b> ${t.category}</p>
                <p><b>Assigned Time:</b> ${t.assigned_time || "N/A"}</p>
                <p><b>Status:</b> ${t.status}</p>

                ${
                    t.status !== "resolved"
                        ? `<button class="complete-btn" onclick="markResolved('${t.request_id}', '${t.technician}')">Mark as Resolved</button>`
                        : `<b style='color:green'>Completed</b>`
                }
            `;

            list.appendChild(div);
        });

    } catch (err) {
        console.error(err);
        document.getElementById("taskList").innerHTML = "Error loading tasks.";
    }
}

async function markResolved(request_id, technician) {
    try {
        const res = await fetch("/technician/update_task", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                request_id,
                status: "resolved",
                technician
            })
        });

        const data = await res.json();

        alert("Task marked as resolved!");

        // Reload tasks
        loadTasks(localStorage.getItem("tech_name"));

    } catch (err) {
        console.error(err);
        alert("Error updating task.");
    }
}
