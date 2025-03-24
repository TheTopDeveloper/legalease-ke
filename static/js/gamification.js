/**
 * Gamification functionality for the Kenya Law Assistant platform
 */

document.addEventListener('DOMContentLoaded', function() {
    initGamificationElements();
});

/**
 * Initialize all gamification UI elements
 */
function initGamificationElements() {
    // Initialize achievement notifications if any are present
    initAchievementNotifications();
    
    // Initialize daily rewards functionality if on the relevant page
    if (document.getElementById('claimRewardBtn')) {
        initDailyRewards();
    }
    
    // Initialize sharing functionality if on the achievements page
    if (document.querySelectorAll('.share-btn').length > 0) {
        initAchievementSharing();
    }
    
    // Initialize activity recording for various user actions
    initActivityTracking();
}

/**
 * Record a user activity and potentially earn points and achievements
 * @param {string} activityType - Type of activity (login, create_case, etc.)
 * @param {string} description - Description of the activity
 * @param {Function} callback - Optional callback function after activity is recorded
 */
function recordActivity(activityType, description, callback) {
    fetch('/gamification/record-activity', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken() // Get CSRF token
        },
        body: JSON.stringify({
            activity_type: activityType,
            description: description
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Check if points were earned
            if (data.points > 0) {
                showPointsNotification(data.points, activityType);
            }
            
            // Check if new level was reached
            if (data.new_level) {
                showLevelUpNotification(data.new_level);
            }
            
            // Check if achievements were earned
            if (data.achievements && data.achievements.length > 0) {
                data.achievements.forEach(achievement => {
                    showAchievementNotification(achievement);
                });
            }
            
            // Execute callback if provided
            if (callback && typeof callback === 'function') {
                callback(data);
            }
        }
    })
    .catch(error => {
        console.error('Error recording activity:', error);
    });
}

/**
 * Show a notification when points are earned
 * @param {number} points - Number of points earned
 * @param {string} activityType - Type of activity
 */
function showPointsNotification(points, activityType) {
    // Create and show a toast notification
    const formattedActivity = activityType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    const toastHtml = `
        <div class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="3000">
            <div class="toast-header bg-success text-white">
                <i class="bi bi-stars me-2"></i>
                <strong class="me-auto">Points Earned</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                <strong>+${points} points</strong> earned for ${formattedActivity}!
            </div>
        </div>
    `;
    
    // Add toast to container and show it
    showToast(toastHtml);
    
    // Optionally play sound
    playSound('points');
}

/**
 * Show a notification when a new level is reached
 * @param {number} level - New level reached
 */
function showLevelUpNotification(level) {
    const toastHtml = `
        <div class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="5000">
            <div class="toast-header bg-primary text-white">
                <i class="bi bi-arrow-up-circle-fill me-2"></i>
                <strong class="me-auto">Level Up!</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                <div class="text-center mb-2">
                    <span class="badge rounded-pill bg-primary px-3 py-2" style="font-size: 1.2rem;">Level ${level}</span>
                </div>
                <p class="mb-0">Congratulations! You've reached level ${level}!</p>
            </div>
        </div>
    `;
    
    // Add toast to container and show it
    showToast(toastHtml);
    
    // Optionally play sound
    playSound('levelup');
}

/**
 * Show a notification when an achievement is earned
 * @param {Object} achievement - Achievement object
 */
function showAchievementNotification(achievement) {
    let iconHtml = '';
    if (achievement.icon && achievement.icon.endsWith('.svg')) {
        iconHtml = `<img src="/static/images/badges/${achievement.icon}" alt="${achievement.name}" class="me-2" style="height: 24px;">`;
    } else {
        iconHtml = `<i class="${achievement.icon || 'bi bi-trophy-fill'} me-2"></i>`;
    }
    
    const toastHtml = `
        <div class="toast achievement-toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="5000">
            <div class="toast-header bg-warning text-dark">
                ${iconHtml}
                <strong class="me-auto">Achievement Unlocked!</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                <div class="d-flex align-items-center mb-2">
                    <div class="flex-shrink-0">
                        ${achievement.icon && achievement.icon.endsWith('.svg') 
                          ? `<img src="/static/images/badges/${achievement.icon}" alt="${achievement.name}" class="me-2" style="height: 48px;">` 
                          : `<i class="${achievement.icon || 'bi bi-trophy-fill'} me-2" style="font-size: 2rem;"></i>`}
                    </div>
                    <div class="flex-grow-1 ms-3">
                        <h5 class="mb-0">${achievement.name}</h5>
                        <p class="mb-0 text-muted">${achievement.points} points</p>
                    </div>
                </div>
                <p class="mb-0">${achievement.description}</p>
            </div>
        </div>
    `;
    
    // Add toast to container and show it
    showToast(toastHtml);
    
    // Optionally play achievement sound
    playSound('achievement');
}

/**
 * Initialize daily rewards functionality
 */
function initDailyRewards() {
    const claimRewardBtn = document.getElementById('claimRewardBtn');
    if (!claimRewardBtn) return;
    
    // Button already has event listeners from daily_reward.html
}

/**
 * Initialize achievement sharing functionality
 */
function initAchievementSharing() {
    // Handled in social_share.html
}

/**
 * Initialize activity tracking for user actions
 */
function initActivityTracking() {
    // Track research activities
    const researchForms = document.querySelectorAll('form[data-track-activity="research"]');
    researchForms.forEach(form => {
        form.addEventListener('submit', function() {
            recordActivity('research', 'Conducted legal research');
        });
    });
    
    // Track case creation
    const caseCreateForms = document.querySelectorAll('form[data-track-activity="create_case"]');
    caseCreateForms.forEach(form => {
        form.addEventListener('submit', function() {
            recordActivity('create_case', 'Created a new case');
        });
    });
    
    // Track document creation
    const docCreateForms = document.querySelectorAll('form[data-track-activity="create_document"]');
    docCreateForms.forEach(form => {
        form.addEventListener('submit', function() {
            recordActivity('create_document', 'Created a new document');
        });
    });
}

/**
 * Initialize achievement notifications
 */
function initAchievementNotifications() {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '11';
        document.body.appendChild(toastContainer);
    }
}

/**
 * Helper function to show a toast notification
 * @param {string} toastHtml - HTML content of the toast
 */
function showToast(toastHtml) {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '11';
        document.body.appendChild(toastContainer);
    }
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show the toast
    const toastElement = toastContainer.querySelector('.toast:last-child');
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

/**
 * Play a sound effect
 * @param {string} soundType - Type of sound to play (points, levelup, achievement)
 */
function playSound(soundType) {
    // Check if audio should be muted based on user preferences
    const muted = localStorage.getItem('gamification_sound_muted') === 'true';
    if (muted) return;
    
    let soundUrl;
    switch (soundType) {
        case 'points':
            soundUrl = '/static/sounds/point.mp3';
            break;
        case 'levelup':
            soundUrl = '/static/sounds/levelup.mp3';
            break;
        case 'achievement':
            soundUrl = '/static/sounds/achievement.mp3';
            break;
        default:
            return;
    }
    
    // Create and play audio
    const audio = new Audio(soundUrl);
    audio.volume = 0.5;
    audio.play().catch(err => {
        console.log('Audio playback failed:', err);
    });
}

/**
 * Get CSRF token from cookies
 * @returns {string} CSRF token
 */
function getCsrfToken() {
    // Get CSRF token from cookie
    const csrfCookie = document.cookie.split(';').find(cookie => cookie.trim().startsWith('csrftoken='));
    if (csrfCookie) {
        return csrfCookie.split('=')[1];
    }
    
    // Fallback to meta tag
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        return csrfMeta.getAttribute('content');
    }
    
    return '';
}

/**
 * Format a date for streak display
 * @param {Date} date - Date to format
 * @returns {string} Formatted date string
 */
function formatStreakDate(date) {
    const options = { month: 'short', day: 'numeric' };
    return date.toLocaleDateString(undefined, options);
}