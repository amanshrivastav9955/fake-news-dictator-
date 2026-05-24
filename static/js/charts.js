// ==========================================================================
// VERIFACT CHART GENERATOR (ADMIN PANEL)
// ==========================================================================

document.addEventListener('DOMContentLoaded', function() {
    
    // Check if Chart is loaded and data objects exist
    if (typeof Chart === 'undefined') return;
    
    const metrics = window.metricsData || {};
    const stats = window.statsData || { real: 0, fake: 0, manual: 0, file: 0 };
    
    // --- 1. ACCURACY BAR CHART ---
    const accCtx = document.getElementById('accuracyChart');
    if (accCtx) {
        const modelKeys = Object.keys(metrics);
        const labels = modelKeys.map(k => k.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()));
        
        // Extract metrics
        const accuracies = modelKeys.map(k => (metrics[k].accuracy * 100).toFixed(1));
        const precisions = modelKeys.map(k => (metrics[k].precision * 100).toFixed(1));
        const recalls = modelKeys.map(k => (metrics[k].recall * 100).toFixed(1));
        const f1s = modelKeys.map(k => (metrics[k].f1_score * 100).toFixed(1));
        
        new Chart(accCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Accuracy (%)',
                        data: accuracies,
                        backgroundColor: 'rgba(139, 92, 246, 0.75)',
                        borderColor: '#8b5cf6',
                        borderWidth: 1.5,
                        borderRadius: 6
                    },
                    {
                        label: 'F1 Score (%)',
                        data: f1s,
                        backgroundColor: 'rgba(6, 182, 212, 0.75)',
                        borderColor: '#06b6d4',
                        borderWidth: 1.5,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim(),
                            font: { family: 'Outfit' }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim(),
                            font: { family: 'Outfit' }
                        }
                    },
                    y: {
                        min: 80,
                        max: 100,
                        grid: {
                            color: 'rgba(255,255,255,0.05)'
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim(),
                            font: { family: 'Outfit' }
                        }
                    }
                }
            }
        });
    }

    // --- 2. VERDICT DISTRIBUTION DOUGHNUT ---
    const distCtx = document.getElementById('distributionChart');
    if (distCtx) {
        const total = stats.real + stats.fake;
        
        // Default to placeholder if empty history
        const dataValues = total === 0 ? [50, 50] : [stats.real, stats.fake];
        const labelText = total === 0 ? ['Real (Demo)', 'Fake (Demo)'] : ['Real News', 'Fake News'];
        
        new Chart(distCtx, {
            type: 'doughnut',
            data: {
                labels: labelText,
                datasets: [{
                    data: dataValues,
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.75)', // success (green)
                        'rgba(239, 68, 68, 0.75)'   // danger (red)
                    ],
                    borderColor: [
                        '#10b981',
                        '#ef4444'
                    ],
                    borderWidth: 1.5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim(),
                            font: { family: 'Outfit' },
                            padding: 15
                        }
                    }
                }
            }
        });
    }
});
