document.addEventListener("DOMContentLoaded", loadTechs);

async function loadTechs() {
    try {
        const res = await fetch("/admin/get_technicians");
        const data = await res.json();

        const table = document.getElementById("techTable");
        table.innerHTML = "";

        data.forEach(t => {
            const tr = document.createElement("tr");

            tr.innerHTML = `
                <td>${t.name}</td>
                <td>${t.role}</td>
                <td>${t.start_time} - ${t.end_time}</td>
                <td>${t.current_load}</td>
                <td>${t.status}</td>
            `;

            table.appendChild(tr);
        });

    } catch (err) {
        console.error(err);
        alert("Error loading technicians");
    }
}
