/**
 * Gamification JavaScript module for handling gamification features
 */

// Toast container to display achievement notifications
document.addEventListener('DOMContentLoaded', function() {
    // Create toast container if it doesn't exist
    if (!document.querySelector('.toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '11';
        document.body.appendChild(toastContainer);
    }
    
    // Record login activity on page load for authenticated users
    if (document.body.dataset.authenticated === 'true') {
        recordActivity('login', 'User logged in');
    }
});

/**
 * Record a user activity and potentially earn points and achievements
 * @param {string} activityType - Type of activity (login, create_case, etc.)
 * @param {string} description - Description of the activity
 * @param {Function} callback - Optional callback function after activity is recorded
 */
function recordActivity(activityType, description, callback) {
    // Create activity data
    const activityData = {
        activity_type: activityType,
        description: description
    };
    
    // Send to server
    fetch('/gamification/record_activity', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(activityData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(`Recorded activity: ${activityType}, earned ${data.points_earned} points`);
            
            // Show points notification
            showPointsNotification(data.points_earned, activityType);
            
            // Show level up notification if applicable
            if (data.level_up) {
                showLevelUpNotification(data.level);
            }
            
            // Show achievement notifications if any new ones were earned
            if (data.new_achievements && data.new_achievements.length > 0) {
                data.new_achievements.forEach(achievement => {
                    showAchievementNotification(achievement);
                });
            }
            
            // Call callback if provided
            if (typeof callback === 'function') {
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
    // Create toast for points
    const pointsToast = document.createElement('div');
    pointsToast.className = 'toast points-toast';
    pointsToast.setAttribute('role', 'alert');
    pointsToast.setAttribute('aria-live', 'assertive');
    pointsToast.setAttribute('aria-atomic', 'true');
    pointsToast.innerHTML = `
        <div class="toast-header bg-success text-white">
            <i class="bi bi-plus-circle me-2"></i>
            <strong class="me-auto">Points Earned</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            <p class="mb-0">+${points} points for ${activityType.replace('_', ' ')}</p>
        </div>
    `;
    
    // Add to container and show
    document.querySelector('.toast-container').appendChild(pointsToast);
    const toast = new bootstrap.Toast(pointsToast, { autohide: true, delay: 3000 });
    toast.show();
    
    // Remove after hidden
    pointsToast.addEventListener('hidden.bs.toast', function() {
        pointsToast.remove();
    });
}

/**
 * Show a notification when a new level is reached
 * @param {number} level - New level reached
 */
function showLevelUpNotification(level) {
    // Create toast for level up
    const levelUpToast = document.createElement('div');
    levelUpToast.className = 'toast level-up-toast';
    levelUpToast.setAttribute('role', 'alert');
    levelUpToast.setAttribute('aria-live', 'assertive');
    levelUpToast.setAttribute('aria-atomic', 'true');
    levelUpToast.innerHTML = `
        <div class="toast-header bg-primary text-white">
            <i class="bi bi-arrow-up-circle me-2"></i>
            <strong class="me-auto">Level Up!</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            <h5 class="mb-1">Congratulations!</h5>
            <p class="mb-0">You've reached level ${level}</p>
        </div>
    `;
    
    // Add to container and show
    document.querySelector('.toast-container').appendChild(levelUpToast);
    const toast = new bootstrap.Toast(levelUpToast, { autohide: true, delay: 5000 });
    toast.show();
    
    // Remove after hidden
    levelUpToast.addEventListener('hidden.bs.toast', function() {
        levelUpToast.remove();
    });
}

/**
 * Show a notification when an achievement is earned
 * @param {Object} achievement - Achievement object
 */
function showAchievementNotification(achievement) {
    // Create toast for achievement
    const achievementToast = document.createElement('div');
    achievementToast.className = 'toast achievement-toast';
    achievementToast.setAttribute('role', 'alert');
    achievementToast.setAttribute('aria-live', 'assertive');
    achievementToast.setAttribute('aria-atomic', 'true');
    achievementToast.innerHTML = `
        <div class="toast-header bg-warning text-dark">
            <i class="${achievement.icon || 'bi bi-trophy'} me-2"></i>
            <strong class="me-auto">Achievement Unlocked!</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            <h5 class="mb-1">${achievement.name}</h5>
            <p class="mb-1">${achievement.description}</p>
            <span class="badge bg-warning text-dark">+${achievement.points} Points</span>
        </div>
    `;
    
    // Add to container and show
    document.querySelector('.toast-container').appendChild(achievementToast);
    const toast = new bootstrap.Toast(achievementToast, { autohide: true, delay: 6000 });
    toast.show();
    
    // Play achievement sound if available
    const achievementSound = document.getElementById('achievement-sound');
    if (achievementSound) {
        achievementSound.play().catch(e => console.log('Could not play achievement sound'));
    }
    
    // Remove after hidden
    achievementToast.addEventListener('hidden.bs.toast', function() {
        achievementToast.remove();
    });
}

// Expose functions globally
window.gamification = {
    recordActivity,
    showPointsNotification,
    showLevelUpNotification,
    showAchievementNotification
};