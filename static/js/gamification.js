/**
 * Gamification JavaScript module for handling gamification features
 */

// Store gamification state
const gamificationState = {
    dailyRewardClaimed: false,
    lastStreak: 0,
    achievements: []
};

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
    
    // Initialize reward box animations if on daily rewards page
    initDailyRewards();
    
    // Initialize achievement sharing
    initAchievementSharing();
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

/**
 * Initialize daily rewards functionality
 */
function initDailyRewards() {
    const rewardBox = document.getElementById('daily-reward-box');
    if (!rewardBox) return;
    
    // Add click handler to reward box
    rewardBox.addEventListener('click', function() {
        if (gamificationState.dailyRewardClaimed) return;
        
        // Visual effect before claiming
        rewardBox.classList.add('pulse');
        
        setTimeout(() => {
            // Claim reward via AJAX
            fetch('/gamification/claim_daily_reward', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show reward animation
                    rewardBox.classList.remove('pulse');
                    rewardBox.classList.add('claimed');
                    
                    // Update state
                    gamificationState.dailyRewardClaimed = true;
                    
                    // Show token reward
                    const rewardAmount = document.createElement('div');
                    rewardAmount.className = 'reward-amount';
                    rewardAmount.innerHTML = `<span class="tokens">+${data.tokens} tokens</span>`;
                    rewardBox.appendChild(rewardAmount);
                    
                    // Update UI elements
                    const tokenDisplay = document.getElementById('user-tokens');
                    if (tokenDisplay) {
                        tokenDisplay.textContent = data.total_tokens;
                    }
                    
                    // Show streak status
                    if (data.streak_days > 0) {
                        const streakInfo = document.getElementById('streak-info');
                        if (streakInfo) {
                            streakInfo.textContent = `Current streak: ${data.streak_days} days`;
                            
                            // Highlight if longest streak was achieved
                            if (data.streak_days > gamificationState.lastStreak && data.streak_days > 1) {
                                streakInfo.classList.add('text-success');
                                streakInfo.innerHTML += ' <span class="badge bg-success">New record!</span>';
                            }
                        }
                    }
                    
                    // Achievement earned for streak
                    if (data.achievement_earned) {
                        showAchievementNotification(data.achievement_earned);
                    }
                    
                    // Update streak state
                    gamificationState.lastStreak = data.streak_days;
                    
                    // Update UI message
                    const rewardMessage = document.getElementById('reward-message');
                    if (rewardMessage) {
                        rewardMessage.textContent = 'Reward claimed! Come back tomorrow for more.';
                    }
                    
                    // Play sound effect if available
                    const rewardSound = document.getElementById('reward-sound');
                    if (rewardSound) {
                        rewardSound.play().catch(e => console.log('Could not play reward sound'));
                    }
                }
            })
            .catch(error => {
                console.error('Error claiming reward:', error);
                rewardBox.classList.remove('pulse');
            });
        }, 800);
    });
}

/**
 * Initialize achievement sharing functionality
 */
function initAchievementSharing() {
    // Set up share buttons for achievements
    const shareButtons = document.querySelectorAll('.achievement-share-btn');
    shareButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const achievementId = this.dataset.achievementId;
            const shareType = this.dataset.shareType || 'twitter';
            
            // Record sharing activity
            recordActivity('share_achievement', `Shared achievement ${achievementId} on ${shareType}`);
            
            // Generate share URL based on type
            let shareUrl = '';
            const achievementName = this.dataset.achievementName || 'an achievement';
            const shareText = encodeURIComponent(`I just earned the ${achievementName} badge on the Kenyan Legal Assistant platform! #LegalTech #Achievement`);
            const appUrl = encodeURIComponent(window.location.origin);
            
            switch(shareType) {
                case 'twitter':
                    shareUrl = `https://twitter.com/intent/tweet?text=${shareText}&url=${appUrl}`;
                    break;
                case 'linkedin':
                    shareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${appUrl}&title=${shareText}`;
                    break;
                case 'facebook':
                    shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${appUrl}&quote=${shareText}`;
                    break;
                case 'whatsapp':
                    shareUrl = `https://wa.me/?text=${shareText} ${appUrl}`;
                    break;
            }
            
            // Open share window
            if (shareUrl) {
                window.open(shareUrl, '_blank', 'width=600,height=400');
            }
        });
    });
}

/**
 * Format a date for streak display
 * @param {Date} date - Date to format
 * @returns {string} Formatted date string
 */
function formatStreakDate(date) {
    return date.toLocaleDateString('en-US', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric' 
    });
}

// Expose functions globally
window.gamification = {
    recordActivity,
    showPointsNotification,
    showLevelUpNotification,
    showAchievementNotification,
    initDailyRewards,
    initAchievementSharing
};