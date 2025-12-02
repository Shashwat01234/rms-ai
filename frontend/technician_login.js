document.getElementById("loginBtn").addEventListener("click", async () => {
    const name = document.getElementById("name").value.trim();
    const password = document.getElementById("password").value.trim();

    const res = await fetch("/technician/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, password })
    });

    const data = await res.json();

    if (data.status === "success") {
        alert("Login successful!");

        // IMPORTANT: Save correct key
        localStorage.setItem("technician_name", name);
        localStorage.setItem("technician_role", data.role);

        window.location.href = "technician_tasks.html";
    } else {
        alert(data.message);
    }
});
