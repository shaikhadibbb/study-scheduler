// Courses Controller

// --- SELECTORS ---
const courseForm = document.getElementById("course-crud-form");
const courseCodeInput = document.getElementById("course-code");
const courseNameInput = document.getElementById("course-name");
const courseCreditsInput = document.getElementById("course-credits");
const courseDifficultyInput = document.getElementById("course-difficulty");
const courseDiffVal = document.getElementById("course-diff-val");
const courseTypeInput = document.getElementById("course-type");
const courseExamInput = document.getElementById("course-exam");
const courseDeadlineInput = document.getElementById("course-deadline");

const btnCancelEdit = document.getElementById("btn-cancel-edit");
const btnSubmitCourse = document.getElementById("btn-submit-course");
const formCardTitle = document.getElementById("form-card-title");

const activeCoursesTbody = document.getElementById("active-courses-tbody");
const pastGradesTbody = document.getElementById("past-grades-tbody");
const semGpaSummary = document.getElementById("sem-gpa-summary");

// State
let isEditing = false;
let editingId = "";

// --- LOADER FUNCTIONS ---

async function loadCoursesPageData() {
    try {
        await Promise.all([
            loadActiveCourses(),
            loadHistoricalGrades()
        ]);
    } catch (err) {
        showNotification(err.message, "danger");
    }
}

async function loadActiveCourses() {
    const courses = await authFetch("/courses");
    
    if (courses.length === 0) {
        activeCoursesTbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    No courses added yet. Use the form above to add your first course.
                </td>
            </tr>
        `;
        return;
    }
    
    activeCoursesTbody.innerHTML = courses.map(c => {
        const rgb = getCourseColorRGB(c.id);
        const examStr = c.exam_date ? new Date(c.exam_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : "Not Set";
        const deadlineStr = c.assignment_deadline ? new Date(c.assignment_deadline).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : "None";
        
        return `
            <tr>
                <td><span class="subject-badge" style="--badge-color-rgb: ${rgb}">${c.id}</span></td>
                <td><strong>${c.name}</strong></td>
                <td>${c.credits}</td>
                <td><span style="color: var(--accent-secondary); font-weight: 600;">${c.difficulty}/5</span></td>
                <td style="text-transform: capitalize;">${c.subject_type}</td>
                <td>
                    <div style="font-size: 0.9rem;">Exam: ${examStr}</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">Deadline: ${deadlineStr}</div>
                </td>
                <td><code style="background-color: var(--bg-tertiary); padding: 0.2rem 0.4rem; border-radius: 4px;">${c.historical_avg.toFixed(2)}x</code></td>
                <td style="text-align: right;">
                    <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                        <button class="btn btn-secondary" style="padding: 0.3rem 0.6rem; font-size: 0.8rem;" onclick="triggerEdit('${c.id}', '${c.name.replace(/'/g, "\\'")}', ${c.credits}, ${c.difficulty}, '${c.subject_type}', '${c.exam_date || ''}', '${c.assignment_deadline || ''}')">Edit</button>
                        <button class="btn btn-danger" style="padding: 0.3rem 0.6rem; font-size: 0.8rem;" onclick="triggerDelete('${c.id}')">Delete</button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

async function loadHistoricalGrades() {
    const grades = await authFetch("/grades");
    
    if (grades.length === 0) {
        pastGradesTbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    No past grade profile found.
                </td>
            </tr>
        `;
        semGpaSummary.innerHTML = "";
        return;
    }

    // Render grades table
    pastGradesTbody.innerHTML = grades.map(g => `
        <tr>
            <td>Semester ${g.semester}</td>
            <td><strong>${g.course_id}</strong></td>
            <td>${g.course_id} - Course Detail</td>
            <td>${g.credits}</td>
            <td><strong>${g.marks}</strong>/100</td>
            <td><span class="subject-badge" style="--badge-color-rgb: 99, 102, 241">${g.grade}</span></td>
        </tr>
    `).join("");

    // Calculate Semester GPAs
    const semGrades = {};
    grades.forEach(g => {
        if (!semGrades[g.semester]) {
            semGrades[g.semester] = [];
        }
        semGrades[g.semester].push(g);
    });

    semGpaSummary.innerHTML = "";
    Object.keys(semGrades).forEach(semNum => {
        const list = semGrades[semNum];
        const totalCredits = list.reduce((sum, g) => sum + g.credits, 0);
        const weightedMarks = list.reduce((sum, g) => sum + (g.marks * g.credits), 0);
        const avgMarks = weightedMarks / totalCredits;
        
        const gpa = avgMarks / 10.0;
        
        const summaryCard = document.createElement("div");
        summaryCard.className = "card";
        summaryCard.style.padding = "1rem";
        summaryCard.style.backgroundColor = "var(--bg-tertiary)";
        summaryCard.innerHTML = `
            <div style="font-size: 0.85rem; color: var(--text-secondary); font-weight: 500;">SEMESTER ${semNum}</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: var(--accent-primary); margin-top: 0.25rem;">${gpa.toFixed(2)}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">${totalCredits} Credits &bull; ${avgMarks.toFixed(1)}% Avg</div>
        `;
        semGpaSummary.appendChild(summaryCard);
    });
}

// --- FORM HANDLING ---

courseDifficultyInput.addEventListener("input", (e) => {
    courseDiffVal.textContent = `${e.target.value}/5`;
});

courseForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const code = courseCodeInput.value.trim().toUpperCase();
    const name = courseNameInput.value.trim();
    const credits = parseInt(courseCreditsInput.value);
    const difficulty = parseInt(courseDifficultyInput.value);
    const subjectType = courseTypeInput.value;
    const examDate = courseExamInput.value || null;
    const assignmentDeadline = courseDeadlineInput.value || null;

    const payload = {
        id: code,
        name: name,
        credits: credits,
        difficulty: difficulty,
        subject_type: subjectType,
        exam_date: examDate,
        assignment_deadline: assignmentDeadline
    };

    try {
        if (isEditing) {
            await authFetch(`/courses/${editingId}`, {
                method: "PUT",
                body: JSON.stringify(payload)
            });
            showNotification(`Course ${editingId} updated successfully.`, "success");
        } else {
            await authFetch("/courses", {
                method: "POST",
                body: JSON.stringify(payload)
            });
            showNotification(`Course ${code} created successfully.`, "success");
        }
        
        resetForm();
        await loadActiveCourses();
    } catch (err) {
        showNotification(err.message, "danger");
    }
});

// --- EDIT/DELETE TRIGGERS ---

window.triggerEdit = function(id, name, credits, difficulty, subjectType, examDate, deadline) {
    isEditing = true;
    editingId = id;
    
    formCardTitle.textContent = `Edit Course: ${id}`;
    courseCodeInput.value = id;
    courseCodeInput.disabled = true;
    
    courseNameInput.value = name;
    courseCreditsInput.value = credits;
    courseDifficultyInput.value = difficulty;
    courseDiffVal.textContent = `${difficulty}/5`;
    courseTypeInput.value = subjectType;
    courseExamInput.value = examDate ? examDate.split("T")[0] : "";
    courseDeadlineInput.value = deadline ? deadline.split("T")[0] : "";
    
    btnCancelEdit.style.display = "inline-flex";
    btnSubmitCourse.textContent = "Update Course";
    
    courseForm.scrollIntoView({ behavior: 'smooth' });
};

window.triggerDelete = async function(id) {
    if (!confirm(`Are you sure you want to delete ${id}? This deletes all related study logs and schedule slots.`)) {
        return;
    }
    
    try {
        await authFetch(`/courses/${id}`, {
            method: "DELETE"
        });
        showNotification(`Course ${id} deleted successfully.`, "success");
        
        if (isEditing && editingId === id) {
            resetForm();
        }
        
        await loadActiveCourses();
    } catch (err) {
        showNotification(err.message, "danger");
    }
};

function resetForm() {
    isEditing = false;
    editingId = "";
    
    formCardTitle.textContent = "Add New Course";
    courseForm.reset();
    courseCodeInput.disabled = false;
    courseDifficultyInput.value = 3;
    courseDiffVal.textContent = "3/5";
    
    btnCancelEdit.style.display = "none";
    btnSubmitCourse.textContent = "Save Course";
}

btnCancelEdit.addEventListener("click", resetForm);

// Initial Load
window.addEventListener("load", () => {
    if (getToken()) {
        loadCoursesPageData();
    }
});
