// Analytics Controller

// --- SELECTORS ---
const aiInsightsContainer = document.getElementById("ai-insights-container");

// --- INITIALIZE & LOAD ---
async function loadAnalyticsData() {
    try {
        const [activeCourses, predVsActual, gradeCorrelation, focusTrend, logs] = await Promise.all([
            authFetch("/courses"),
            authFetch("/stats/predicted-vs-actual"),
            authFetch("/stats/grade-correlation"),
            authFetch("/stats/focus-trend"),
            authFetch("/logs")
        ]);
        
        renderAIInsights(activeCourses);
        renderPredVsActualChart(predVsActual);
        renderGradeCorrelationChart(gradeCorrelation);
        renderFocusTrendChart(focusTrend);
        renderSubjectTypeDistribution(logs);
        
    } catch (err) {
        showNotification(err.message, "danger");
    }
}

// --- RENDERING FUNCTIONS ---

function renderAIInsights(courses) {
    const calibratedCourses = courses.filter(c => c.historical_avg !== 1.0);
    
    if (calibratedCourses.length === 0) {
        aiInsightsContainer.innerHTML = `
            <div style="background-color: rgba(255,255,255,0.05); padding: 0.75rem 1rem; border-radius: var(--radius-sm);">
                <strong>Model Status:</strong> The scheduling weights are currently at standard baselines. Log more study sessions under the Logger page, and the feedback loop will automatically start scaling your prediction coefficients.
            </div>
        `;
        return;
    }
    
    let insightsHtml = calibratedCourses.map(c => {
        const factor = c.historical_avg;
        if (factor > 1.0) {
            const percentage = Math.round((factor - 1.0) * 100);
            return `
                <div style="background-color: rgba(239, 68, 68, 0.05); border-left: 4px solid var(--danger); padding: 0.75rem 1rem; border-radius: var(--radius-sm); margin-bottom: 0.5rem;">
                    <strong>Scale Up:</strong> You take on average <strong>${percentage}% longer</strong> than expected on <strong>${c.name} (${c.id})</strong>. The scheduler has calibrated its coefficient to <strong>${factor.toFixed(2)}x</strong> to allocate extra prep time.
                </div>
            `;
        } else {
            const percentage = Math.round((1.0 - factor) * 100);
            return `
                <div style="background-color: rgba(16, 185, 129, 0.05); border-left: 4px solid var(--success); padding: 0.75rem 1rem; border-radius: var(--radius-sm); margin-bottom: 0.5rem;">
                    <strong>Scale Down:</strong> You complete study sessions <strong>${percentage}% faster</strong> than expected on <strong>${c.name} (${c.id})</strong>. The scheduler has adjusted its coefficient to <strong>${factor.toFixed(2)}x</strong> to avoid over-allocating time.
                </div>
            `;
        }
    }).join("");
    
    aiInsightsContainer.innerHTML = `
        <div style="margin-bottom: 0.5rem; font-weight: 500; font-size: 0.9rem; color: var(--text-secondary);">
            The closed-loop feedback mechanism has dynamically modified the following prediction multipliers:
        </div>
        ${insightsHtml}
    `;
}

function renderPredVsActualChart(data) {
    const ctx = document.getElementById("chart-pred-vs-actual").getContext("2d");
    
    const labels = data.map(d => d.course_id);
    const predicted = data.map(d => d.predicted_hours);
    const actual = data.map(d => d.actual_hours);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Predicted Hours',
                    data: predicted,
                    backgroundColor: 'rgba(99, 102, 241, 0.6)',
                    borderColor: 'rgba(99, 102, 241, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Actual Hours',
                    data: actual,
                    backgroundColor: 'rgba(168, 85, 247, 0.6)',
                    borderColor: 'rgba(168, 85, 247, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } }
            },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' }, title: { display: true, text: 'Hours', color: '#94a3b8' } }
            }
        }
    });
}

function renderGradeCorrelationChart(data) {
    const ctx = document.getElementById("chart-grade-correlation").getContext("2d");
    
    const points = data.map(d => ({
        x: d.study_hours,
        y: d.marks,
        course_id: d.course_id
    }));
    
    new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Historical Courses (Sem 1-4)',
                data: points,
                backgroundColor: 'rgba(245, 158, 11, 0.8)',
                borderColor: 'rgba(245, 158, 11, 1)',
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8' } },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const p = context.raw;
                            return `Course: ${p.course_id} | Studied: ${p.x.toFixed(1)}h | Marks: ${p.y}%`;
                        }
                    }
                }
            },
            scales: {
                x: { 
                    ticks: { color: '#94a3b8' }, 
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    title: { display: true, text: 'Total Studied Hours', color: '#94a3b8' }
                },
                y: { 
                    ticks: { color: '#94a3b8' }, 
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    title: { display: true, text: 'Exam Marks (%)', color: '#94a3b8' },
                    min: 50,
                    max: 100
                }
            }
        }
    });
}

function renderFocusTrendChart(data) {
    const ctx = document.getElementById("chart-focus-trend").getContext("2d");
    
    const labels = data.map(d => new Date(d.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
    const scores = data.map(d => d.avg_focus);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Focus Index Trend',
                data: scores,
                borderColor: 'rgba(6, 182, 212, 1)',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { 
                    ticks: { color: '#94a3b8' }, 
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    title: { display: true, text: 'Focus Level (1-10)', color: '#94a3b8' },
                    min: 1,
                    max: 10
                }
            }
        }
    });
}

function renderSubjectTypeDistribution(logs) {
    const ctx = document.getElementById("chart-subject-type").getContext("2d");
    
    const typeHours = { math: 0, programming: 0, theory: 0 };
    
    const typeMap = {
        "CS305": "programming", "MA302": "math", "CS307": "theory",
        "CS309": "programming", "CS311": "theory", "HU301": "theory",
        "CS101": "programming", "MA101": "math", "PH101": "theory",
        "EE101": "theory", "HU101": "theory", "CS102": "programming",
        "MA102": "math", "CH101": "theory", "ME101": "theory",
        "CS104": "theory", "CS201": "math", "CS203": "programming",
        "CS205": "theory", "CS207": "theory", "MA201": "math",
        "CS202": "theory", "CS204": "theory", "CS206": "theory",
        "CS208": "theory", "CS210": "theory"
    };

    logs.forEach(l => {
        const type = typeMap[l.course_id] || "theory";
        typeHours[type] += l.actual_hours;
    });

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Math / Quantitative', 'Programming / Hands-on', 'Theory / Analytical'],
            datasets: [{
                data: [typeHours.math, typeHours.programming, typeHours.theory],
                backgroundColor: [
                    'rgba(59, 130, 246, 0.7)',  // Blue
                    'rgba(168, 85, 247, 0.7)', // Purple
                    'rgba(16, 185, 129, 0.7)'  // Green
                ],
                borderColor: [
                    'rgba(59, 130, 246, 1)',
                    'rgba(168, 85, 247, 1)',
                    'rgba(16, 185, 129, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: 'Inter' } }
                }
            }
        }
    });
}

// Initial load
window.addEventListener("load", () => {
    if (getToken()) {
        loadAnalyticsData();
    }
});
