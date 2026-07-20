// technician_login.js
function toast(msg, type = "info") {
  const c = document.getElementById("toast-container");
  const t = document.createElement("div");
  t.className = `toast ${type}`; t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => { t.style.animation = "slide-out 0.3s ease forwards"; setTimeout(() => t.remove(), 300); }, 3500);
}

document.getElementById("loginBtn").addEventListener("click", doLogin);
document.addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });

async function doLogin() {
  const name     = document.getElementById("name").value.trim();
  const password = document.getElementById("password").value.trim();
  const btn      = document.getElementById("loginBtn");

  if (!name || !password) { toast("Please enter name and password.", "error"); return; }

  btn.disabled = true; btn.textContent = "Signing in…";
  try {
    const res  = await fetch("/technician/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, password })
    });
    const data = await res.json();
    if (data.status === "success") {
      localStorage.setItem("technician_name", name);
      localStorage.setItem("technician_role", data.role);
      toast(`Welcome, ${name}!`, "success");
      setTimeout(() => { window.location.href = "technician_tasks.html"; }, 700);
    } else {
      toast(data.message || "Invalid credentials.", "error");
      btn.disabled = false; btn.textContent = "Sign In";
    }
  } catch {
    toast("Cannot connect to server.", "error");
    btn.disabled = false; btn.textContent = "Sign In";
  }
}
