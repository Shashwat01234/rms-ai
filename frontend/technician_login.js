async function techLogin() {
    const name = document.getElementById("name").value.trim();
    const password = document.getElementById("password").value.trim();

    if (!name || !password) {
        alert("Please enter both Name and Password");
        return;
    }

    try {
        const res = await fetch("/technician/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, password })
        });

        const data = await res.json();

        if (data.status === "success") {
            alert("Login Successful!");

            localStorage.setItem("tech_name", data.name);
            localStorage.setItem("tech_role", data.role);

            window.location.href = "technician_tasks.html";
        } else {
            alert(data.message);
        }
    } catch (err) {
        console.error(err);
        alert("Server error");
    }
}
