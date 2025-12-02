document.addEventListener("DOMContentLoaded", () => {
    const techName = localStorage.getItem("technician_name");
    if (!techName) {
        alert("Login expired");
        window.location.href = "technician_login.html";
    }

    loadTasks(techName);
});

async function loadTasks(name) {
    const res = await fetch(`/technician/get_tasks?name=${name}`);
    const data = await res.json();

    const taskContainer = document.getElementById("taskList");
    taskContainer.innerHTML = "";

    if (data.length === 0) {
        taskContainer.innerHTML = "<p>No tasks assigned.</p>";
        return;
    }

    data.forEach(task => {
        const div = document.createElement("div");
        div.className = "task";

        div.innerHTML = `
            <p><b>Issue:</b> ${task.query}</p>
            <p><b>Category:</b> ${task.category}</p>
            <p><b>Student ID:</b> ${task.student_id}</p>
            <p><b>Status:</b> <span class="status-badge ${task.status}">${task.status}</span></p>

            <button class="btn accept-btn" onclick="markAccepted('${task.request_id}')">
                Accept Task
            </button>

            <button class="btn resolve-btn" onclick="markResolved('${task.request_id}')">
                Mark Resolved
            </button>
        `;

        taskContainer.appendChild(div);
    });
}

async function markAccepted(requestId) {
    await updateStatus(requestId, "assigned");
}

async function markResolved(requestId) {
    await updateStatus(requestId, "resolved");
}

async function updateStatus(id, status) {
    const res = await fetch("/admin/update_status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            request_id: id,
            status: status
        })
    });

    const data = await res.json();

    if (data.message === "updated") {
        alert("Status updated!");
        location.reload();
    } else {
        alert("Error updating task: " + JSON.stringify(data));
    }
}
