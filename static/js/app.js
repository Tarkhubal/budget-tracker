// Budget Tracker JavaScript

// Flash message auto-hide
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            setTimeout(function() {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 300);
        }, 5000);
    });
});

// Form validation helpers
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(function(field) {
        if (!field.value.trim()) {
            showFieldError(field, 'This field is required');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    // Validate amount fields
    const amountFields = formElement.querySelectorAll('input[type="number"]');
    amountFields.forEach(function(field) {
        if (field.value && parseFloat(field.value) <= 0) {
            showFieldError(field, 'Amount must be greater than 0');
            isValid = false;
        }
    });
    
    return isValid;
}

function showFieldError(field, message) {
    clearFieldError(field);
    const errorElement = document.createElement('span');
    errorElement.className = 'form-error';
    errorElement.textContent = message;
    field.parentNode.appendChild(errorElement);
    field.style.borderColor = '#dc3545';
}

function clearFieldError(field) {
    const existingError = field.parentNode.querySelector('.form-error');
    if (existingError) {
        existingError.remove();
    }
    field.style.borderColor = '#e9ecef';
}

// Currency formatting
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Date formatting
function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).format(new Date(date));
}

// Animate numbers
function animateNumber(element, start, end, duration = 1000) {
    const startTime = Date.now();
    const range = end - start;
    
    function updateNumber() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out)
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        
        const current = start + (range * easeProgress);
        element.textContent = formatCurrency(current);
        
        if (progress < 1) {
            requestAnimationFrame(updateNumber);
        }
    }
    
    requestAnimationFrame(updateNumber);
}

// Progress bar animation
function animateProgressBar(element, percentage, duration = 1000) {
    const startTime = Date.now();
    
    function updateProgress() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out)
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        
        const current = percentage * easeProgress;
        element.style.width = Math.min(current, 100) + '%';
        
        if (progress < 1) {
            requestAnimationFrame(updateProgress);
        }
    }
    
    requestAnimationFrame(updateProgress);
}

// Initialize animations when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Animate card amounts
    const cardAmounts = document.querySelectorAll('.card-amount');
    cardAmounts.forEach(function(element) {
        const text = element.textContent.replace(/[$,]/g, '');
        const amount = parseFloat(text);
        if (!isNaN(amount)) {
            element.textContent = '$0.00';
            setTimeout(function() {
                animateNumber(element, 0, amount, 1200);
            }, 300);
        }
    });
    
    // Animate progress bars
    const progressBars = document.querySelectorAll('.progress-fill');
    progressBars.forEach(function(element) {
        const width = element.style.width;
        const percentage = parseFloat(width);
        if (!isNaN(percentage)) {
            element.style.width = '0%';
            setTimeout(function() {
                animateProgressBar(element, percentage, 1000);
            }, 600);
        }
    });
});

// Chart drawing utilities
function drawChart(canvas, data, type = 'bar') {
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    
    // Set canvas size
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    
    const padding = 40;
    const chartWidth = rect.width - 2 * padding;
    const chartHeight = rect.height - 2 * padding;
    
    if (type === 'bar') {
        drawBarChart(ctx, data, padding, chartWidth, chartHeight, rect.width, rect.height);
    } else if (type === 'pie') {
        drawPieChart(ctx, data, rect.width / 2, rect.height / 2, Math.min(rect.width, rect.height) / 2 - 20);
    }
}

function drawBarChart(ctx, data, padding, chartWidth, chartHeight, canvasWidth, canvasHeight) {
    if (data.length === 0) return;
    
    const maxValue = Math.max(...data.map(d => d.value));
    const scale = maxValue > 0 ? chartHeight / maxValue : 1;
    
    // Draw axes
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvasHeight - padding);
    ctx.lineTo(canvasWidth - padding, canvasHeight - padding);
    ctx.stroke();
    
    // Draw bars
    const barWidth = chartWidth / data.length * 0.7;
    const barSpacing = chartWidth / data.length * 0.3;
    
    data.forEach((item, index) => {
        const x = padding + index * (barWidth + barSpacing) + barSpacing / 2;
        const barHeight = item.value * scale;
        const y = canvasHeight - padding - barHeight;
        
        // Create gradient
        const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight);
        gradient.addColorStop(0, '#667eea');
        gradient.addColorStop(1, '#764ba2');
        
        // Draw bar
        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barWidth, barHeight);
        
        // Draw value label
        if (barHeight > 20) {
            ctx.fillStyle = 'white';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(formatCurrency(item.value), x + barWidth / 2, y + 20);
        }
        
        // Draw category label
        ctx.fillStyle = '#333';
        ctx.font = '11px Arial';
        ctx.textAlign = 'center';
        ctx.save();
        ctx.translate(x + barWidth / 2, canvasHeight - padding + 15);
        ctx.rotate(-Math.PI / 4);
        ctx.fillText(item.label, 0, 0);
        ctx.restore();
    });
}

function drawPieChart(ctx, data, centerX, centerY, radius) {
    if (data.length === 0) return;
    
    const total = data.reduce((sum, item) => sum + item.value, 0);
    let currentAngle = -Math.PI / 2;
    
    const colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
        '#9966FF', '#FF9F40', '#C9CBCF', '#4BC0C0'
    ];
    
    data.forEach((item, index) => {
        const sliceAngle = (item.value / total) * 2 * Math.PI;
        
        // Draw slice
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
        ctx.closePath();
        ctx.fillStyle = colors[index % colors.length];
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Draw label
        const labelAngle = currentAngle + sliceAngle / 2;
        const labelX = centerX + Math.cos(labelAngle) * (radius * 0.7);
        const labelY = centerY + Math.sin(labelAngle) * (radius * 0.7);
        
        ctx.fillStyle = 'white';
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`${Math.round((item.value / total) * 100)}%`, labelX, labelY);
        
        currentAngle += sliceAngle;
    });
}

// Smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', function() {
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Alt + I: Add Income
    if (e.altKey && e.key === 'i') {
        e.preventDefault();
        window.location.href = '/add_income';
    }
    
    // Alt + E: Add Expense
    if (e.altKey && e.key === 'e') {
        e.preventDefault();
        window.location.href = '/add_expense';
    }
    
    // Alt + B: Add Budget
    if (e.altKey && e.key === 'b') {
        e.preventDefault();
        window.location.href = '/add_budget';
    }
    
    // Alt + D: Dashboard
    if (e.altKey && e.key === 'd') {
        e.preventDefault();
        window.location.href = '/';
    }
});

// Local storage utilities
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
    } catch (e) {
        console.warn('Could not save to localStorage:', e);
    }
}

function loadFromLocalStorage(key, defaultValue = null) {
    try {
        const stored = localStorage.getItem(key);
        return stored ? JSON.parse(stored) : defaultValue;
    } catch (e) {
        console.warn('Could not load from localStorage:', e);
        return defaultValue;
    }
}

// Form state persistence
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        const formId = form.id || form.action.split('/').pop();
        
        // Load saved form data
        const savedData = loadFromLocalStorage(`form_${formId}`, {});
        Object.keys(savedData).forEach(function(fieldName) {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field && field.type !== 'hidden') {
                if (field.type === 'checkbox') {
                    field.checked = savedData[fieldName];
                } else {
                    field.value = savedData[fieldName];
                }
            }
        });
        
        // Save form data on change
        form.addEventListener('input', function(e) {
            const field = e.target;
            if (field.name && field.type !== 'hidden') {
                savedData[field.name] = field.type === 'checkbox' ? field.checked : field.value;
                saveToLocalStorage(`form_${formId}`, savedData);
            }
        });
        
        // Clear saved data on successful submit
        form.addEventListener('submit', function() {
            localStorage.removeItem(`form_${formId}`);
        });
    });
});

// Responsive table handling
function makeTablesResponsive() {
    const tables = document.querySelectorAll('.transaction-table');
    tables.forEach(function(table) {
        if (window.innerWidth <= 768) {
            table.classList.add('mobile-table');
        } else {
            table.classList.remove('mobile-table');
        }
    });
}

window.addEventListener('resize', makeTablesResponsive);
document.addEventListener('DOMContentLoaded', makeTablesResponsive);

// Export functions for use in templates
window.BudgetTracker = {
    formatCurrency,
    formatDate,
    animateNumber,
    animateProgressBar,
    drawChart,
    validateForm,
    saveToLocalStorage,
    loadFromLocalStorage
};