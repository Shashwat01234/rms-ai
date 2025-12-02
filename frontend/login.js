document.getElementById("loginBtn").addEventListener("click", async () => {
    const student_id = document.getElementById("student_id").value.trim();
    const password = document.getElementById("password").value.trim();

    if (!student_id || !password) {
        alert("Please enter both Student ID and Password");
        return;
    }

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_id, password })
        });

        const data = await response.json();

        if (data.status === "success") {
            alert("Login Successful!");

            // Save student ID for future pages
            localStorage.setItem("student_id", student_id);
            localStorage.setItem("student_name", data.name);

            // Redirect to Complaint Page
            window.location.href = "complaint.html";
        } else {
            alert(data.message || "Login failed");
        }

    } catch (error) {
        console.error("Error:", error);
        alert("Server is not responding");
    }
});
