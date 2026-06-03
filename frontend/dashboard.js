// Dashboard Controller

// --- SELECTORS ---
const welcomeTitle = document.getElementById("welcome-title");
const dashboardDateStr = document.getElementById("dashboard-date-str");
const btnRegenerate = document.getElementById("btn-regenerate-schedule");
const btnTriggerLogPast = document.getElementById("btn-trigger-log-past");

// Stats
const adherencePct = document.getElementById("adherence-pct");
const adherenceCircle = document.getElementById("adherence-circle");
const focusScoreVal = document.getElementById("focus-score-val");
const hoursDevVal = document.getElementById("hours-dev-val");

// Containers
const todayFocusContent = document.getElementById("today-focus-content");
const weeklyPlanTimeline = document.getElementById("weekly-plan-timeline");
const warningsCard = document.getElementById("warnings-card");
const warningsContainer = document.getElementById("warnings-container");

// Modal Elements
const logModal = document.getElementById("log-session-modal");
const logForm = document.getElementById("session-log-form");
const logCourseId = document.getElementById("log-course-id");
const logCourseName = document.getElementById("log-course-name");
const logDate = document.getElementById("log-date");
const logPlanned = document.getElementById("log-planned");
const logPlannedVal = document.getElementById("log-planned-val");
const logActual = document.getElementById("log-actual");
const logActualVal = document.getElementById("log-actual-val");
const logFocus = document.getElementById("log-focus");
const logFocusVal = document.getElementById("log-focus-val");
const logNotes = document.getElementById("log-notes");
const logCompleted = document.getElementById("log-completed");

const btnCloseModal = document.getElementById("btn-close-modal");
const btnCancelModal = document.getElementById("btn-cancel-modal");
const modalHeading = document.getElementById("modal-heading");

let activeCourses = [];

// Fallback courses in case backend API is down or empty
const fallbackCourses = [
    { id: "CS305", name: "Computational Learning in AI", credits: 3, difficulty: 5, exam_date: "2026-12-15", subject_type: "programming", historical_avg: 1.0 },
    { id: "MA302", name: "Probability & Statistics", credits: 3, difficulty: 4, exam_date: "2026-12-12", subject_type: "math", historical_avg: 1.0 },
    { id: "CS307", name: "Blockchain Technology", credits: 3, difficulty: 2, exam_date: "2026-12-18", subject_type: "theory", historical_avg: 1.0 },
    { id: "CS309", name: "Web Technology", credits: 3, difficulty: 3, exam_date: "2026-12-10", subject_type: "programming", historical_avg: 1.0 },
    { id: "CS311", name: "Software Engineering", credits: 3, difficulty: 3, exam_date: "2026-12-20", subject_type: "theory", historical_avg: 1.0 },
    { id: "HU301", name: "Professional Ethics", credits: 2, difficulty: 1, exam_date: "2026-12-08", subject_type: "theory", historical_avg: 1.0 }
];

// --- DATE FORMATTER ---
function getFriendlyDateString(date) {
    return date.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}

// --- INITIAL DATA LOAD ---
async function loadDashboardData() {
    const user = getCurrentUser();
    if (!user) return;
    
    // Personalize greeting
    const formattedName = user.full_name || (user.sub.includes('@') ? user.sub.split('@')[0] : user.sub);
    const capitalizedName = formattedName.charAt(0).toUpperCase() + formattedName.slice(1);
    welcomeTitle.textContent = `Hey ${capitalizedName}, Semester 6`;
    dashboardDateStr.textContent = getFriendlyDateString(new Date());
    
    try {
        // Fetch current courses list
        activeCourses = await authFetch("/courses").catch((err) => {
            console.warn("Backend offline or request failed. Loading fallback courses.", err);
            return fallbackCourses;
        });
        
        if (!activeCourses || activeCourses.length === 0) {
            activeCourses = fallbackCourses;
        }
        
        // Load stats
        await loadStats().catch(e => console.warn("Failed to load stats:", e));
        
        // Load schedules
        await loadSchedules().catch(e => console.warn("Failed to load schedules:", e));
        
        // Load past logs to calculate focus index, deviation and warnings
        await loadLogsAndWarnings().catch(e => console.warn("Failed to load logs/warnings:", e));
        
    } catch (err) {
        showNotification(err.message, "danger");
    }
}

// --- CORE STATS HANDLER ---
async function loadStats() {
    const adherence = await authFetch("/stats/adherence");
    const rate = adherence.adherence_rate;
    adherencePct.textContent = `${rate}%`;
    adherenceCircle.style.background = `conic-gradient(var(--accent-primary) ${rate}%, var(--bg-tertiary) ${rate}%)`;
}

// --- LOAD LOGS & COMPUTE ADAPTIVE WARNINGS ---
async function loadLogsAndWarnings() {
    const logs = await authFetch("/logs");
    
    if (logs.length > 0) {
        // 1. Focus Index (Avg focus score)
        const avgFocus = logs.reduce((sum, l) => sum + l.focus_score, 0) / logs.length;
        focusScoreVal.textContent = avgFocus.toFixed(1);
        
        // 2. Time Variance (Actual - Planned)
        const actualSum = logs.reduce((sum, l) => sum + l.actual_hours, 0);
        const plannedSum = logs.reduce((sum, l) => sum + l.planned_hours, 0);
        const dev = actualSum - plannedSum;
        const sign = dev >= 0 ? "+" : "";
        hoursDevVal.textContent = `${sign}${dev.toFixed(1)}h`;
        
        // 3. Dynamic Adaptive Warnings
        const lastWeek = new Date();
        lastWeek.setDate(lastWeek.getDate() - 7);
        
        const recentLogs = logs.filter(l => new Date(l.date) >= lastWeek);
        const courseHours = {};
        
        // Group by current courses
        activeCourses.forEach(c => {
            courseHours[c.id] = { planned: 0, actual: 0, name: c.name };
        });
        
        recentLogs.forEach(l => {
            if (courseHours[l.course_id]) {
                courseHours[l.course_id].planned += l.planned_hours;
                courseHours[l.course_id].actual += l.actual_hours;
            }
        });
        
        const warnings = [];
        
        for (const cid in courseHours) {
            const stat = courseHours[cid];
            if (stat.planned > 0 && stat.actual < stat.planned) {
                const deficit = stat.planned - stat.actual;
                if (deficit >= 1.0) {
                    warnings.push({
                        type: "shortfall",
                        text: `Shortfall Warning: You fell <strong>${deficit.toFixed(1)}h short</strong> on <strong>${stat.name}</strong> this week. Try planning more morning sessions or adjusting difficulty.`
                    });
                }
            }
        }
        
        if (logs.length > 3) {
            const completedCount = logs.filter(l => l.completed).length;
            const completedRate = (completedCount / logs.length) * 100;
            if (completedRate < 60) {
                warnings.push({
                    type: "adherence",
                    text: `Low Goal Adherence: You've completed only <strong>${completedRate.toFixed(0)}%</strong> of your logged study goals. Try planning shorter 1-hour study chunks.`
                });
            }
        }

        // Render warnings
        if (warnings.length > 0) {
            warningsCard.style.display = "block";
            warningsContainer.innerHTML = warnings.map(w => `
                <div class="alert alert-warning" style="margin-bottom: 0;">
                    <div>${w.text}</div>
                </div>
            `).join("");
        } else {
            warningsCard.style.display = "none";
        }
    } else {
        focusScoreVal.textContent = "N/A";
        hoursDevVal.textContent = "0.0h";
        warningsCard.style.display = "none";
    }
}

// --- TODAY & WEEKLY SCHEDULE TIMELINE ---
async function loadSchedules() {
    const todaySlots = await authFetch("/schedule/today").catch(() => []);
    const weeklyData = await authFetch("/schedule/weekly").catch(() => ({ schedule: {} }));
    const weeklySchedule = weeklyData.schedule;
    
    // 1. Render Today's Focus Card
    if (todaySlots.length === 0) {
        todayFocusContent.innerHTML = `
            <div style="text-align: center; padding: 1.5rem 0;">
                <p style="font-size: 1.1rem; color: var(--text-secondary); margin-bottom: 1rem;">Rest Day - no study slots scheduled. Or log a custom session below.</p>
                <button class="btn btn-secondary" onclick="openCustomLogModal()">Log an Unplanned Session</button>
            </div>
        `;
    } else {
        let slotsHtml = todaySlots.map(s => {
            const course = activeCourses.find(c => c.id === s.course_id) || { name: s.course_id };
            const rgb = getCourseColorRGB(s.course_id);
            const isCompleted = s.completed;
            
            return `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background-color: var(--bg-tertiary); border-radius: var(--radius-md); border-left: 5px solid rgb(${rgb}); margin-bottom: 0.75rem; opacity: ${isCompleted ? 0.6 : 1};">
                    <div>
                        <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                            <span class="subject-badge" style="--badge-color-rgb: ${rgb}">${s.course_id}</span>
                            <strong style="font-size: 1.05rem; ${isCompleted ? 'text-decoration: line-through; color: var(--text-muted);' : ''}">${course.name}</strong>
                        </div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem;">
                            Time slot: <strong style="text-transform: capitalize;">${s.time_slot}</strong> &bull; Scheduled: <strong>${s.allocated_hours} hrs</strong>
                        </div>
                    </div>
                    <div>
                        ${isCompleted ? 
                            `<span style="color: #888; font-size: 0.9rem;">done</span>` :
                            `<button class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;" onclick="openLogModal('${s.course_id}', '${course.name.replace(/'/g, "\\'")}', ${s.allocated_hours}, ${s.id})">Log Session</button>`
                        }
                    </div>
                </div>
            `;
        }).join("");
        todayFocusContent.innerHTML = `<div style="display: flex; flex-direction: column;">${slotsHtml}</div>`;
    }

    // 2. Render Weekly Timeline (Calendar view)
    weeklyPlanTimeline.innerHTML = "";
    
    // Sort keys chronologically
    const sortedDates = Object.keys(weeklySchedule).sort();
    
    if (sortedDates.length === 0) {
        weeklyPlanTimeline.innerHTML = `<p style="color: var(--text-secondary);">No schedule generated yet. Click "Regenerate Weekly" to build one.</p>`;
        return;
    }
    
    sortedDates.forEach(dateStr => {
        const slots = weeklySchedule[dateStr];
        const dateObj = new Date(dateStr);
        const dayName = dateObj.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
        
        let daySlotsHtml = "";
        if (slots.length === 0) {
            daySlotsHtml = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 0.25rem 0;">No study slots scheduled</div>`;
        } else {
            daySlotsHtml = slots.map(s => {
                const rgb = getCourseColorRGB(s.course_id);
                return `
                    <div style="display: inline-flex; align-items: center; gap: 0.5rem; background-color: var(--bg-tertiary); padding: 0.3rem 0.6rem; border-radius: var(--radius-sm); border-left: 3px solid rgb(${rgb}); font-size: 0.8rem; margin: 0.2rem;">
                        <strong>${s.course_id}</strong>: ${s.hours}h (${s.time_slot})
                    </div>
                `;
            }).join(" ");
        }
        
        const dayCard = document.createElement("div");
        dayCard.className = "weekly-day-row";
        dayCard.style.padding = "0.75rem 0";
        dayCard.style.borderBottom = "1px solid var(--border-color)";
        dayCard.innerHTML = `
            <div style="display: grid; grid-template-columns: 100px 1fr; gap: 1rem; align-items: center;">
                <div style="font-weight: 600; font-size: 0.9rem; color: var(--text-secondary);">${dayName}</div>
                <div style="display: flex; flex-wrap: wrap;">${daySlotsHtml}</div>
            </div>
        `;
        weeklyPlanTimeline.appendChild(dayCard);
    });
}

// --- OPEN LOG MODAL (For Scheduled Slot) ---
window.openLogModal = function(courseId, courseName, plannedHours, slotId) {
    modalHeading.textContent = `Log Study Session: ${courseId}`;
    
    logCourseId.value = courseId;
    logCourseName.value = `${courseId} - ${courseName}`;
    logCourseName.style.display = "block";
    
    const existingSelect = document.getElementById("log-course-select");
    if (existingSelect) existingSelect.remove();

    logDate.value = new Date().toISOString().split("T")[0];
    
    // Set planned slider
    logPlanned.value = plannedHours;
    logPlannedVal.textContent = `${plannedHours}h`;
    
    // Set actual slider to match planned
    logActual.value = plannedHours;
    logActualVal.textContent = `${plannedHours}h`;
    
    logFocus.value = 7;
    logFocusVal.textContent = "7/10";
    
    logNotes.value = "";
    logCompleted.checked = true;
    
    logModal.classList.add("active");
};

// --- OPEN CUSTOM LOG MODAL (For Unplanned Subject) ---
window.openCustomLogModal = function() {
    modalHeading.textContent = "Log Unplanned Session";
    logCourseId.value = "";
    
    logCourseName.style.display = "none";
    
    const existingSelect = document.getElementById("log-course-select");
    if (existingSelect) existingSelect.remove();
    
    const select = document.createElement("select");
    select.id = "log-course-select";
    select.className = "form-control";
    select.required = true;
    
    let optionsHtml = activeCourses.map(c => `<option value="${c.id}">${c.id} - ${c.name}</option>`).join("");
    select.innerHTML = `<option value="" disabled selected>Select a Subject</option>${optionsHtml}`;
    
    logCourseName.parentNode.appendChild(select);
    
    logDate.value = new Date().toISOString().split("T")[0];
    logPlanned.value = 2.0;
    logPlannedVal.textContent = "2.0h";
    logActual.value = 2.0;
    logActualVal.textContent = "2.0h";
    logFocus.value = 7;
    logFocusVal.textContent = "7/10";
    logNotes.value = "";
    logCompleted.checked = true;
    
    logModal.classList.add("active");
};

// --- CLOSE MODAL ---
function closeModal() {
    logModal.classList.remove("active");
}

btnCloseModal.addEventListener("click", closeModal);
btnCancelModal.addEventListener("click", closeModal);

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

// --- SUBMIT STUDY LOG FORM ---
logForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    let courseId = logCourseId.value;
    if (!courseId) {
        const select = document.getElementById("log-course-select");
        if (select) courseId = select.value;
    }
    
    if (!courseId) {
        showNotification("Select a subject first", "warning");
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
        
        showNotification("Study log successfully saved.", "success");
        closeModal();
        await loadDashboardData();
    } catch (err) {
        showNotification(err.message, "danger");
    }
});

// --- REGENERATE SCHEDULE BUTTON ---
btnRegenerate.addEventListener("click", async () => {
    btnRegenerate.disabled = true;
    btnRegenerate.textContent = "Generating...";
    try {
        await authFetch("/schedule/weekly");
        showNotification("Weekly schedule generated!", "success");
        await loadDashboardData();
    } catch (err) {
        showNotification(err.message, "danger");
    } finally {
        btnRegenerate.disabled = false;
        btnRegenerate.textContent = "Regenerate Weekly";
    }
});

btnTriggerLogPast.addEventListener("click", () => {
    openCustomLogModal();
});

// Initial trigger
window.addEventListener("load", () => {
    if (getToken()) {
        loadDashboardData();
    }
});
