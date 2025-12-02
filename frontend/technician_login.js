document.addEventListener("DOMContentLoaded", () => {

    const loginBtn = document.getElementById("loginBtn");

    loginBtn.addEventListener("click", async () => {

        const name = document.getElementById("name").value.trim();
        const password = document.getElementById("password").value.trim();

        if (!name || !password) {
            alert("Please enter both name and password.");
            return;
        }

        try {
            const res = await fetch("/technician/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: name,
                    password: password
                })
            });

            const data = await res.json();
            console.log("Technician login response:", data);

            if (data.status === "success") {
                alert("Login successful!");

                // 🔥 IMPORTANT: Save correct key for technician_tasks.js
                localStorage.setItem("technician_name", name);
                localStorage.setItem("technician_role", data.role);

                // Redirect to task dashboard
                window.location.href = "technician_tasks.html";
            } else {
                alert(data.message || "Invalid credentials");
            }

        } catch (err) {
            console.error("Login error:", err);
            alert("Unable to connect to server.");
        }

    });

});

