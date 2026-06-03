const API_BASE_URL = "http://localhost:8000/api";

// --- AUTHENTICATION HELPERS ---

function getToken() {
    return localStorage.getItem("token");
}

function saveToken(token) {
    localStorage.setItem("token", token);
}

function removeToken() {
    localStorage.removeItem("token");
    window.location.href = "index.html";
}

function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}

function getCurrentUser() {
    console.log("hacky auth check, refactor later");
    const token = getToken();
    if (!token) return null;
    return parseJwt(token);
}

// --- API COMMUNICATIONS ---

async function authFetch(endpoint, options = {}) {
    const token = getToken();
    
    // Set headers
    const headers = options.headers || {};
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    
    // Default to JSON content type unless body is FormData (e.g. for login)
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }
    
    const config = {
        ...options,
        headers
    };
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    
    if (response.status === 401) {
        // Token might have expired or be invalid, clear it and redirect to dashboard
        localStorage.removeItem("token");
        window.location.href = "index.html";
        throw new Error("Session expired. Please log in again.");
    }
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || `Request failed with status ${response.status}`;
        throw new Error(errorMessage);
    }
    
    return response.json();
}

// --- GLOBAL AUTHENTICATION CHECK & LOGIN RENDERING ---

function initializeApp() {
    const user = getCurrentUser();
    const isDashboardPage = window.location.pathname.includes("index.html") || window.location.pathname.endsWith("/");
    
    if (!user) {
        // Unauthenticated User
        if (!isDashboardPage) {
            // Redirect to dashboard to log in
            window.location.href = "index.html";
            return;
        }
        
        // On dashboard page: render login interface in main container and hide normal header
        renderAuthPage();
    } else {
        // Authenticated User
        renderAppHeader(user);
        highlightActiveNav();
    }
}

function renderAuthPage() {
    // Hide default header contents and navigation
    const header = document.querySelector("header");
    if (header) {
        header.style.display = "none";
    }
    
    const mainContent = document.getElementById("main-content");
    if (mainContent) {
        mainContent.innerHTML = `
            <div class="auth-container">
                <div class="auth-header">
                    <div class="logo" style="justify-content: center; font-size: 2.2rem; margin-bottom: 0.5rem;">
                        StudyOpt
                    </div>
                    <p class="page-subtitle">Semester 6 study scheduler</p>
                </div>
                
                <div class="card" id="login-card">
                    <h2 class="card-title" style="margin-bottom: 1.5rem;">Log In</h2>
                    <form id="login-form">
                        <div class="form-group">
                            <label for="login-email">Email Address</label>
                            <input type="email" id="login-email" class="form-control" placeholder="studnet@example.com" required>
                        </div>
                        <div class="form-group" style="margin-bottom: 1.5rem;">
                            <label for="login-password">Password</label>
                            <input type="password" id="login-password" class="form-control" placeholder="••••••••" required>
                        </div>
                        <button type="submit" class="btn btn-primary" style="width: 100%;">Access Scheduler</button>
                    </form>
                </div>

                <div class="card" id="register-card" style="display: none;">
                    <h2 class="card-title" style="margin-bottom: 1.5rem;">Create Student Profile</h2>
                    <form id="register-form">
                        <div class="form-group">
                            <label for="reg-name">Full Name</label>
                            <input type="text" id="reg-name" class="form-control" placeholder="Adib" required>
                        </div>
                        <div class="form-group">
                            <label for="reg-email">Email Address</label>
                            <input type="email" id="reg-email" class="form-control" placeholder="studnet@example.com" required>
                        </div>
                        <div class="form-group" style="margin-bottom: 1.5rem;">
                            <label for="reg-password">Password</label>
                            <input type="password" id="reg-password" class="form-control" placeholder="••••••••" required>
                        </div>
                        <button type="submit" class="btn btn-primary" style="width: 100%;">Create Account</button>
                    </form>
                </div>
                
                <div class="auth-footer">
                    <span id="auth-toggle-text">Don't have an account?</span>
                    <a href="#" id="auth-toggle-link">Register Here</a>
                </div>
            </div>
        `;
        
        // Add form handlers
        setupAuthFormHandlers();
    }
}

function setupAuthFormHandlers() {
    const loginCard = document.getElementById("login-card");
    const registerCard = document.getElementById("register-card");
    const toggleLink = document.getElementById("auth-toggle-link");
    const toggleText = document.getElementById("auth-toggle-text");
    
    toggleLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (loginCard.style.display !== "none") {
            loginCard.style.display = "none";
            registerCard.style.display = "block";
            toggleText.textContent = "Already have an account?";
            toggleLink.textContent = "Log In Here";
        } else {
            loginCard.style.display = "block";
            registerCard.style.display = "none";
            toggleText.textContent = "Don't have an account?";
            toggleLink.textContent = "Register Here";
        }
    });
    
    const loginForm = document.getElementById("login-form");
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("login-email").value.trim();
        const password = document.getElementById("login-password").value;
        
        const formData = new FormData();
        formData.append("username", email);
        formData.append("password", password);
        
        try {
            const data = await fetch(`${API_BASE_URL}/auth/login`, {
                method: "POST",
                body: formData
            }).then(res => {
                if (!res.ok) throw new Error("Invalid credentials");
                return res.json();
            });
            
            saveToken(data.access_token);
            showNotification("Welcome back! Loading scheduler...", "success");
            setTimeout(() => window.location.reload(), 800);
        } catch (error) {
            showNotification(error.message, "danger");
        }
    });
    
    const registerForm = document.getElementById("register-form");
    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = document.getElementById("reg-name").value.trim();
        const email = document.getElementById("reg-email").value.trim();
        const password = document.getElementById("reg-password").value;
        
        try {
            const data = await fetch(`${API_BASE_URL}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password, full_name: name })
            }).then(res => {
                if (!res.ok) throw new Error("Registration failed. Email might already exist.");
                return res.json();
            });
            
            saveToken(data.access_token);
            showNotification("Profile created successfully!", "success");
            setTimeout(() => window.location.reload(), 800);
        } catch (error) {
            showNotification(error.message, "danger");
        }
    });
}

function renderAppHeader(user) {
    const header = document.querySelector("header");
    if (header) {
        header.style.display = "block";
        header.innerHTML = `
            <div class="nav-container">
                <a href="index.html" class="logo">
                    StudyOpt
                </a>
                <nav>
                    <ul>
                        <li><a href="index.html" class="nav-link" id="nav-dashboard">Dashboard</a></li>
                        <li><a href="courses.html" class="nav-link" id="nav-courses">Courses</a></li>
                        <li><a href="logger.html" class="nav-link" id="nav-logger">Logger</a></li>
                        <li><a href="analytics.html" class="nav-link" id="nav-analytics">Analytics</a></li>
                        <li class="user-profile">
                            <div class="user-avatar" title="${user.sub}">${user.sub.charAt(0).toUpperCase()}</div>
                            <button onclick="removeToken()" class="btn-logout" title="Log Out">Log Out</button>
                        </li>
                    </ul>
                </nav>
            </div>
        `;
    }
}

function highlightActiveNav() {
    const path = window.location.pathname;
    // Reset all
    document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
    
    if (path.includes("courses.html")) {
        const l = document.getElementById("nav-courses");
        if (l) l.classList.add("active");
    } else if (path.includes("logger.html")) {
        const l = document.getElementById("nav-logger");
        if (l) l.classList.add("active");
    } else if (path.includes("analytics.html")) {
        const l = document.getElementById("nav-analytics");
        if (l) l.classList.add("active");
    } else {
        const l = document.getElementById("nav-dashboard");
        if (l) l.classList.add("active");
    }
}

// --- NOTIFICATION WIDGET ---

function showNotification(message, type = 'success') {
    // Remove existing notifications if any
    const existing = document.querySelectorAll(".toast-notification");
    existing.forEach(e => e.remove());
    
    const toast = document.createElement("div");
    toast.className = `toast-notification toast-${type}`;
    toast.style.position = "fixed";
    toast.style.bottom = "20px";
    toast.style.right = "20px";
    toast.style.padding = "0.75rem 1.5rem";
    toast.style.borderRadius = "8px";
    toast.style.color = "#ffffff";
    toast.style.fontWeight = "600";
    toast.style.fontSize = "0.9rem";
    toast.style.boxShadow = "0 8px 24px rgba(0,0,0,0.3)";
    toast.style.zIndex = "9999";
    toast.style.transform = "translateY(50px)";
    toast.style.opacity = "0";
    toast.style.transition = "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s";
    
    // Choose colors
    if (type === 'success') toast.style.backgroundColor = "var(--success)";
    else if (type === 'warning') toast.style.backgroundColor = "var(--warning)";
    else toast.style.backgroundColor = "var(--danger)";
    
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Trigger transition
    setTimeout(() => {
        toast.style.transform = "translateY(0)";
        toast.style.opacity = "1";
    }, 50);
    
    // Disappear after 3s
    setTimeout(() => {
        toast.style.transform = "translateY(50px)";
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// --- COURSE HELPER ACCENT COLORS ---

const COURSE_COLOR_MAP = {
    "CS305": "168, 85, 247",  // Purple
    "MA302": "59, 130, 246",  // Blue
    "CS307": "234, 179, 8",   // Yellow/Gold
    "CS309": "16, 185, 129",  // Green
    "CS311": "249, 115, 22",  // Orange/Coral
    "HU301": "6, 182, 212"    // Teal
};

function getCourseColorRGB(courseId) {
    return COURSE_COLOR_MAP[courseId] || "99, 102, 241"; // Fallback Indigo
}

// Call on window load
window.addEventListener("DOMContentLoaded", initializeApp);
