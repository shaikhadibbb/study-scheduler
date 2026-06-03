// Logger Controller

// --- SELECTORS ---
const loggerForm = document.getElementById("study-logger-form");
const logCourseId = document.getElementById("log-course-id");
const logDate = document.getElementById("log-date");
const logPlanned = document.getElementById("log-planned");
const logPlannedVal = document.getElementById("log-planned-val");
const logActual = document.getElementById("log-actual");
const logActualVal = document.getElementById("log-actual-val");
const logFocus = document.getElementById("log-focus");
const logFocusVal = document.getElementById("log-focus-val");
const logNotes = document.getElementById("log-notes");
const logCompleted = document.getElementById("log-completed");
const logsHistoryTbody = document.getElementById("logs-history-tbody");

// Local fallbacks in case backend is offline
const fallbackCourses = [
    { id: "CS305", name: "Computational Learning in AI" },
    { id: "MA302", name: "Probability & Statistics" },
    { id: "CS307", name: "Blockchain Technology" },
    { id: "CS309", name: "Web Technology" },
    { id: "CS311", name: "Software Engineering" },
    { id: "HU301", name: "Professional Ethics" }
];

// --- INITIALIZE & LOAD ---
async function loadLoggerPageData() {
    logDate.value = new Date().toISOString().split("T")[0];
    
    try {
        await populateCourseSelects().catch(e => console.warn("Failed to populate course selects:", e));
        await loadLogsHistory().catch(e => console.warn("Failed to load logs history:", e));
    } catch (err) {
        showNotification(err.message, "danger");
    }
}

async function populateCourseSelects() {
    // Fetch active courses with a fallback
    const activeCourses = await authFetch("/courses").catch((err) => {
        console.warn("Backend offline. Using local course fallbacks.", err);
        return fallbackCourses;
    });
    
    // Fetch grades (past courses)
    const grades = await authFetch("/grades").catch(() => []);
    
    const uniqueCourseIds = new Set(activeCourses.map(c => c.id));
    const coursesList = activeCourses.map(c => ({ id: c.id, name: c.name, type: "active" }));
    
    grades.forEach(g => {
        if (!uniqueCourseIds.has(g.course_id)) {
            uniqueCourseIds.add(g.course_id);
            coursesList.push({ id: g.course_id, name: `${g.course_id} (Past Course)`, type: "past" });
        }
    });

    if (coursesList.length === 0) {
        // Double-check fallback safety
        fallbackCourses.forEach(c => coursesList.push({ id: c.id, name: c.name, type: "active" }));
    }

    logCourseId.innerHTML = `
        <option value="" disabled selected>Select Course Subject</option>
        ${coursesList.map(c => `
            <option value="${c.id}">${c.id} - ${c.name}</option>
        `).join("")}
    `;
}

async function loadLogsHistory() {
    const logs = await authFetch("/logs");
    
    if (logs.length === 0) {
        logsHistoryTbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    No study sessions logged yet.
                </td>
            </tr>
        `;
        return;
    }
    
    logsHistoryTbody.innerHTML = logs.slice(0, 15).map(l => {
        const rgb = getCourseColorRGB(l.course_id);
        const dateStr = new Date(l.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
        
        return `
            <tr style="opacity: ${l.completed ? 1 : 0.7}">
                <td>${dateStr}</td>
                <td><span class="subject-badge" style="--badge-color-rgb: ${rgb}">${l.course_id}</span></td>
                <td>${l.planned_hours} hrs</td>
                <td><strong style="color: var(--accent-secondary);">${l.actual_hours} hrs</strong></td>
                <td><span style="color: var(--warning); font-weight: 600;">Focus: ${l.focus_score}/10</span></td>
                <td>
                    ${l.completed ? 
                        `<span style="color: var(--success); font-weight: 600;">Completed</span>` :
                        `<span style="color: var(--warning); font-weight: 600;">Incomplete</span>`
                    }
                </td>
                <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${l.notes || ''}">
                    <span style="font-size: 0.85rem; color: var(--text-secondary);">${l.notes || '—'}</span>
                </td>
            </tr>
        `;
    }).join("");
}

// --- SLIDER EVENT BINDINGS ---
logPlanned.addEventListener("input", (e) => {
    logPlannedVal.textContent = `${e.target.value}h`;
});
logActual.addEventListener("input", (e) => {
    logActualVal.textContent = `${e.target.value}h`;
});
logFocus.addEventListener("input", (e) => {
    logFocusVal.textContent = `${e.target.value}/10`;
});

// --- SUBMIT FORM ---
loggerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const courseId = logCourseId.value;
    if (!courseId) {
        showNotification("Please select a subject.", "warning");
        return;
    }
    
    const payload = {
        course_id: courseId,
        date: logDate.value,
        planned_hours: parseFloat(logPlanned.value),
        actual_hours: parseFloat(logActual.value),
        focus_score: parseInt(logFocus.value),
        completed: logCompleted.checked,
        notes: logNotes.value.trim()
    };
    
    try {
        await authFetch("/logs", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        
        showNotification("Study session logged successfully.", "success");
        
        loggerForm.reset();
        logPlanned.value = 2.0;
        logPlannedVal.textContent = "2.0h";
        logActual.value = 2.0;
        logActualVal.textContent = "2.0h";
        logFocus.value = 7;
        logFocusVal.textContent = "7/10";
        logCompleted.checked = true;
        logDate.value = new Date().toISOString().split("T")[0];
        
        await loadLogsHistory();
    } catch (err) {
        showNotification(err.message, "danger");
    }
});

// Initial load
window.addEventListener("load", () => {
    if (getToken()) {
        loadLoggerPageData();
    }
});
