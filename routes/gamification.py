"""
Routes for gamification features like achievements, challenges, and rewards.
"""

import json
import math
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import desc

from app import db
from models import User, UserProfile, Achievement, UserAchievement, Challenge, UserChallenge, Activity
from utils.gamification import GamificationService

gamification_bp = Blueprint('gamification', __name__)

# Constants for gamification
POINTS_PER_LEVEL = 100  # Points needed to advance to the next level
DAILY_REWARD_TOKENS = 2  # Base tokens for daily rewards

# Activity types and points
ACTIVITY_POINTS = {
    'login': 5,
    'create_case': 15,
    'update_case': 5,
    'create_document': 10,
    'research': 20,
    'complete_challenge': 0,  # Challenge points are defined by the challenge
    'share_achievement': 10,
    'claim_daily_reward': 5
}

# Activity icons and colors for UI
ACTIVITY_ICONS = {
    'login': {'icon': 'door-open', 'color': 'primary'},
    'create_case': {'icon': 'briefcase', 'color': 'success'},
    'update_case': {'icon': 'pencil', 'color': 'info'},
    'create_document': {'icon': 'file-earmark-text', 'color': 'warning'},
    'research': {'icon': 'search', 'color': 'danger'},
    'complete_challenge': {'icon': 'flag-fill', 'color': 'warning'},
    'share_achievement': {'icon': 'share', 'color': 'info'},
    'claim_daily_reward': {'icon': 'gift', 'color': 'success'}
}

@gamification_bp.route('/')
@login_required
def dashboard():
    """Gamification dashboard showing user progress and achievements"""
    # Get or create user profile
    user_profile = GamificationService.get_or_create_profile(current_user)
    
    # Calculate level progress
    level_progress = (user_profile.total_points % POINTS_PER_LEVEL) / POINTS_PER_LEVEL * 100
    points_to_next_level = POINTS_PER_LEVEL * (user_profile.level + 1) - user_profile.total_points
    
    # Get earned achievements
    earned_achievements = [ua.achievement for ua in current_user.achievements]
    all_achievements = Achievement.query.filter_by(is_active=True).all()
    
    # Get recent achievements (last 4)
    recent_achievements = [ua.achievement for ua in UserAchievement.query
                          .filter_by(user_id=current_user.id)
                          .order_by(UserAchievement.earned_at.desc())
                          .limit(4)]
    
    # Get active challenges
    user_challenges = UserChallenge.query.filter_by(
        user_id=current_user.id, 
        status='accepted'
    ).all()
    
    active_challenges = []
    for uc in user_challenges:
        challenge = uc.challenge
        if not challenge.is_ongoing():
            continue
            
        # Get progress data
        progress_data = uc.get_progress()
        requirements = challenge.get_requirements()
        
        # Calculate progress percentage
        target = requirements.get('target', 1)
        progress = progress_data.get('progress', 0)
        progress_percentage = min(int(progress / target * 100), 100)
        
        active_challenges.append({
            'id': challenge.id,
            'title': challenge.title,
            'description': challenge.description,
            'challenge_type': challenge.challenge_type,
            'points': challenge.points,
            'target': target,
            'progress': progress,
            'progress_percentage': progress_percentage,
            'end_date': challenge.end_date
        })
    
    # Get recent activities
    recent_activities = []
    activities = Activity.query.filter_by(user_id=current_user.id).order_by(Activity.created_at.desc()).limit(10)
    
    for activity in activities:
        icon_info = ACTIVITY_ICONS.get(activity.activity_type, {'icon': 'circle', 'color': 'secondary'})
        recent_activities.append({
            'id': activity.id,
            'activity_type': activity.activity_type,
            'description': activity.description,
            'points': activity.points,
            'created_at': activity.created_at,
            'icon': icon_info['icon'],
            'color': icon_info['color']
        })
    
    return render_template('gamification/dashboard.html', 
                           user_profile=user_profile,
                           level_progress=level_progress,
                           points_to_next_level=points_to_next_level,
                           earned_achievements=earned_achievements,
                           all_achievements=all_achievements,
                           recent_achievements=recent_achievements,
                           active_challenges=active_challenges,
                           recent_activities=recent_activities)

@gamification_bp.route('/achievements')
@login_required
def achievements():
    """View all achievements in the system"""
    # Get or create user profile
    user_profile = GamificationService.get_or_create_profile(current_user)
    
    # Calculate level progress
    level_progress = (user_profile.total_points % POINTS_PER_LEVEL) / POINTS_PER_LEVEL * 100
    points_to_next_level = POINTS_PER_LEVEL * (user_profile.level + 1) - user_profile.total_points
    
    # Get earned and all achievements
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
    earned_achievements = [ua.achievement for ua in user_achievements]
    earned_ids = [a.id for a in earned_achievements]
    
    all_achievements = Achievement.query.filter_by(is_active=True).all()
    locked_achievements = [a for a in all_achievements if a.id not in earned_ids]
    
    # Calculate completion percentage
    completion_percentage = round(len(earned_achievements) / len(all_achievements) * 100) if all_achievements else 0
    
    return render_template('gamification/achievements.html',
                          user_profile=user_profile,
                          level_progress=level_progress,
                          points_to_next_level=points_to_next_level,
                          earned_achievements=earned_achievements,
                          locked_achievements=locked_achievements,
                          all_achievements=all_achievements,
                          earned_ids=earned_ids,
                          completion_percentage=completion_percentage)

@gamification_bp.route('/challenges')
@login_required
def challenges():
    """View all active challenges"""
    # Get active challenges for the user
    active_challenges = GamificationService.get_active_challenges(current_user)
    
    return render_template('gamification/challenges.html',
                          active_challenges=active_challenges)

@gamification_bp.route('/accept_challenge/<int:challenge_id>', methods=['POST'])
@login_required
def accept_challenge(challenge_id):
    """Accept a challenge"""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    # Check if challenge is active
    if not challenge.is_ongoing():
        flash('This challenge is no longer active.', 'danger')
        return redirect(url_for('gamification.challenges'))
    
    # Check if already accepted
    existing = UserChallenge.query.filter_by(
        user_id=current_user.id,
        challenge_id=challenge_id
    ).first()
    
    if existing:
        flash('You have already accepted this challenge.', 'info')
    else:
        # Create new user challenge
        user_challenge = UserChallenge(
            user_id=current_user.id,
            challenge_id=challenge_id,
            status='accepted',
            progress=json.dumps({'progress': 0})
        )
        db.session.add(user_challenge)
        db.session.commit()
        
        flash('Challenge accepted! Good luck!', 'success')
    
    return redirect(url_for('gamification.challenges'))

@gamification_bp.route('/leaderboard')
@login_required
def leaderboard():
    """View user leaderboard"""
    # Get top users by points
    top_users = UserProfile.query.order_by(UserProfile.total_points.desc()).limit(10).all()
    
    # Get current user's rank
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    
    if user_profile:
        # Count users with more points
        user_rank = UserProfile.query.filter(UserProfile.total_points > user_profile.total_points).count() + 1
    else:
        user_rank = UserProfile.query.count()
    
    return render_template('gamification/leaderboard.html',
                          top_users=top_users,
                          user_profile=user_profile,
                          user_rank=user_rank)

@gamification_bp.route('/daily_rewards')
@login_required
def daily_rewards():
    """Daily rewards page for claiming tokens"""
    # Get or create user profile
    user_profile = GamificationService.get_or_create_profile(current_user)
    
    # Check if user can claim daily reward
    can_claim = user_profile.can_claim_daily_reward()
    
    return render_template('gamification/daily_reward.html',
                          user_profile=user_profile,
                          can_claim=can_claim)

@gamification_bp.route('/claim_daily_reward', methods=['POST'])
@login_required
def claim_daily_reward():
    """Claim daily reward tokens"""
    # Get or create user profile
    user_profile = GamificationService.get_or_create_profile(current_user)
    
    # Check if user can claim
    if not user_profile.can_claim_daily_reward():
        return jsonify({
            'success': False,
            'message': 'You have already claimed your daily reward.'
        })
    
    # Calculate streak bonus for display
    streak_bonus = 0
    if user_profile.streak_days >= 7:
        streak_bonus = 3
    elif user_profile.streak_days >= 5:
        streak_bonus = 2
    elif user_profile.streak_days >= 3:
        streak_bonus = 1
    
    # Claim reward (tokens already added to user in the claim_daily_reward method)
    tokens_earned = user_profile.claim_daily_reward()
    
    # Record activity
    activity = Activity(
        user_id=current_user.id,
        activity_type='claim_daily_reward',
        description='Claimed daily reward',
        points=ACTIVITY_POINTS['claim_daily_reward']
    )
    db.session.add(activity)
    
    # Add points
    user_profile.add_points(ACTIVITY_POINTS['claim_daily_reward'])
    
    # Check for streak achievement
    achievement_earned = None
    if user_profile.streak_days >= 7:
        # Check if user already has the streak achievement
        streak_achievement = Achievement.query.filter_by(name='Streak Master').first()
        if streak_achievement:
            existing = UserAchievement.query.filter_by(
                user_id=current_user.id,
                achievement_id=streak_achievement.id
            ).first()
            
            if not existing:
                # Award the achievement
                new_achievement = UserAchievement(
                    user_id=current_user.id,
                    achievement_id=streak_achievement.id
                )
                db.session.add(new_achievement)
                
                # Add achievement points
                user_profile.add_points(streak_achievement.points)
                
                # Set achievement for response
                achievement_earned = {
                    'id': streak_achievement.id,
                    'name': streak_achievement.name,
                    'description': streak_achievement.description,
                    'category': streak_achievement.category,
                    'points': streak_achievement.points,
                    'icon': streak_achievement.icon
                }
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'base_tokens': DAILY_REWARD_TOKENS,
        'streak_bonus': streak_bonus,
        'tokens': tokens_earned,
        'total_tokens': current_user.tokens_available,
        'streak_days': user_profile.streak_days,
        'achievement_earned': achievement_earned
    })

@gamification_bp.route('/social_share/<int:achievement_id>')
@login_required
def social_share(achievement_id):
    """Generate social share links and record sharing activity"""
    # Get achievement
    achievement = Achievement.query.get_or_404(achievement_id)
    
    # Check if user has earned this achievement
    user_achievement = UserAchievement.query.filter_by(
        user_id=current_user.id,
        achievement_id=achievement_id
    ).first_or_404()
    
    return render_template('gamification/social_share.html',
                          achievement=achievement,
                          earned_at=user_achievement.earned_at)

@gamification_bp.route('/record_activity', methods=['POST'])
@login_required
def record_activity():
    """API endpoint to record user activity and award points"""
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request'})
    
    data = request.json
    activity_type = data.get('activity_type')
    description = data.get('description')
    
    if not activity_type or activity_type not in ACTIVITY_POINTS:
        return jsonify({'success': False, 'message': 'Invalid activity type'})
    
    # Record activity
    result = GamificationService.record_activity(current_user, activity_type, description)
    
    return jsonify({
        'success': True,
        'points_earned': result.get('points', 0),
        'level_up': result.get('level_up', False),
        'level': result.get('level', 1),
        'new_achievements': result.get('new_achievements', [])
    })

@gamification_bp.route('/check_achievements/<int:user_id>')
@login_required
def check_achievements(user_id):
    """Check if user has earned any new achievements"""
    # Only admins or the user themselves can check
    if current_user.id != user_id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = User.query.get_or_404(user_id)
    
    # Check achievements
    GamificationService.check_achievements(user)
    
    return jsonify({'success': True})