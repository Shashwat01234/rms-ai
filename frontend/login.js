// ── Toast helper ─────────────────────────────
function toast(msg, type = "info") {
  const c = document.getElementById("toast-container");
  if (!c) return;
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => {
    t.style.animation = "slide-out 0.3s ease forwards";
    setTimeout(() => t.remove(), 300);
  }, 3500);
}

// ── Show/hide password ────────────────────────
document.getElementById("eyeBtn").addEventListener("click", () => {
  const p = document.getElementById("password");
  const btn = document.getElementById("eyeBtn");
  p.type = p.type === "password" ? "text" : "password";
  btn.textContent = p.type === "password" ? "👁" : "🙈";
});

// ── Login ─────────────────────────────────────
document.getElementById("loginBtn").addEventListener("click", async () => {
  const student_id = document.getElementById("student_id").value.trim();
  const password   = document.getElementById("password").value.trim();
  const btn        = document.getElementById("loginBtn");

  if (!student_id || !password) {
    toast("Please fill in both fields.", "error"); return;
  }

  btn.disabled = true;
  btn.textContent = "Signing in…";

  try {
    const res  = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id, password }),
    });
    const data = await res.json();

    if (data.status === "success") {
      localStorage.setItem("student_id",   student_id);
      localStorage.setItem("student_name", data.name);
      toast("Welcome back, " + data.name + "!", "success");
      setTimeout(() => { window.location.href = "complaint.html"; }, 800);
    } else {
      toast(data.message || "Invalid credentials.", "error");
      btn.disabled = false; btn.textContent = "Sign In";
    }
  } catch {
    toast("Cannot connect to server.", "error");
    btn.disabled = false; btn.textContent = "Sign In";
  }
});

// Enter key
document.addEventListener("keydown", e => {
  if (e.key === "Enter") document.getElementById("loginBtn").click();
});
