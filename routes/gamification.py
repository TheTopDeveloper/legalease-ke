from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import UserProfile, Achievement, UserAchievement, Activity, Challenge, UserChallenge

# Create blueprint
gamification_bp = Blueprint('gamification', __name__, url_prefix='/gamification')

@gamification_bp.route('/')
@login_required
def dashboard():
    """Gamification dashboard showing user progress and achievements"""
    # Get user profile, creating one if it doesn't exist
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()
    
    # Update streak if user is visiting
    profile.update_streak()
    db.session.commit()
    
    # Get user achievements
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
    earned_achievement_ids = [ua.achievement_id for ua in user_achievements]
    
    # Get all achievements, marking which ones the user has earned
    all_achievements = Achievement.query.filter_by(is_active=True).all()
    for achievement in all_achievements:
        achievement.earned = achievement.id in earned_achievement_ids
    
    # Get active challenges
    active_challenges = Challenge.query.filter(
        Challenge.is_active == True,
        Challenge.start_date <= datetime.utcnow(),
        Challenge.end_date >= datetime.utcnow()
    ).all()
    
    # Get user's active challenges
    user_challenges = UserChallenge.query.filter_by(
        user_id=current_user.id,
        status='accepted'
    ).all()
    
    # Get recent activities
    recent_activities = Activity.query.filter_by(
        user_id=current_user.id
    ).order_by(Activity.created_at.desc()).limit(10).all()
    
    # Calculate progress to next level
    next_level_points = (profile.level * 100)
    current_level_points = ((profile.level - 1) * 100)
    level_progress = ((profile.total_points - current_level_points) / 
                      (next_level_points - current_level_points) * 100)
    
    return render_template(
        'gamification/dashboard.html',
        profile=profile,
        achievements=all_achievements,
        active_challenges=active_challenges,
        user_challenges=user_challenges,
        recent_activities=recent_activities,
        level_progress=level_progress
    )

@gamification_bp.route('/achievements')
@login_required
def achievements():
    """View all achievements in the system"""
    # Get user achievements
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
    earned_achievement_ids = [ua.achievement_id for ua in user_achievements]
    
    # Get achievements by category
    achievement_categories = {}
    for category in ['case', 'document', 'research', 'general']:
        achievements = Achievement.query.filter_by(
            category=category, 
            is_active=True
        ).all()
        
        # Mark achievements as earned or not
        for achievement in achievements:
            achievement.earned = achievement.id in earned_achievement_ids
            
        achievement_categories[category] = achievements
    
    return render_template(
        'gamification/achievements.html',
        achievement_categories=achievement_categories,
        earned_count=len(earned_achievement_ids),
        total_count=Achievement.query.filter_by(is_active=True).count()
    )

@gamification_bp.route('/challenges')
@login_required
def challenges():
    """View all active challenges"""
    # Get active challenges
    active_challenges = Challenge.query.filter(
        Challenge.is_active == True,
        Challenge.start_date <= datetime.utcnow(),
        Challenge.end_date >= datetime.utcnow()
    ).all()
    
    # Get user's accepted challenges
    user_challenges = UserChallenge.query.filter_by(user_id=current_user.id).all()
    user_challenge_ids = {uc.challenge_id: uc for uc in user_challenges}
    
    # Mark challenges as accepted, completed, or available
    for challenge in active_challenges:
        if challenge.id in user_challenge_ids:
            user_challenge = user_challenge_ids[challenge.id]
            challenge.status = user_challenge.status
            challenge.progress = user_challenge.get_progress() if user_challenge.progress else {}
        else:
            challenge.status = 'available'
            challenge.progress = {}
    
    # Split challenges by type
    daily_challenges = [c for c in active_challenges if c.challenge_type == 'daily']
    weekly_challenges = [c for c in active_challenges if c.challenge_type == 'weekly']
    special_challenges = [c for c in active_challenges if c.challenge_type not in ['daily', 'weekly']]
    
    return render_template(
        'gamification/challenges.html',
        daily_challenges=daily_challenges,
        weekly_challenges=weekly_challenges,
        special_challenges=special_challenges
    )

@gamification_bp.route('/challenge/<int:challenge_id>/accept', methods=['POST'])
@login_required
def accept_challenge(challenge_id):
    """Accept a challenge"""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    # Check if challenge is active and within date range
    now = datetime.utcnow()
    if not challenge.is_active or challenge.start_date > now or challenge.end_date < now:
        flash('This challenge is not currently available.', 'warning')
        return redirect(url_for('gamification.challenges'))
    
    # Check if user has already accepted this challenge
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
            progress='{}'
        )
        db.session.add(user_challenge)
        
        # Record activity
        activity = Activity(
            user_id=current_user.id,
            activity_type='accept_challenge',
            description=f'Accepted challenge: {challenge.title}',
            points=5
        )
        db.session.add(activity)
        
        # Add points to user profile
        profile = UserProfile.query.filter_by(user_id=current_user.id).first()
        if profile:
            profile.add_points(5)
        
        db.session.commit()
        flash('Challenge accepted!', 'success')
    
    return redirect(url_for('gamification.challenges'))

@gamification_bp.route('/leaderboard')
@login_required
def leaderboard():
    """View user leaderboard"""
    # Get top users by total points
    top_users = UserProfile.query.order_by(UserProfile.total_points.desc()).limit(20).all()
    
    # Get user's rank
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    if user_profile:
        # Count users with more points
        user_rank = UserProfile.query.filter(
            UserProfile.total_points > user_profile.total_points
        ).count() + 1
    else:
        user_rank = "N/A"
    
    return render_template(
        'gamification/leaderboard.html',
        top_users=top_users,
        user_rank=user_rank
    )

@gamification_bp.route('/record_activity', methods=['POST'])
@login_required
def record_activity():
    """API endpoint to record user activity and award points"""
    # This endpoint would be called from JavaScript
    data = request.json
    if not data or 'activity_type' not in data:
        return jsonify({'error': 'Missing activity data'}), 400
    
    activity_type = data.get('activity_type')
    description = data.get('description', '')
    
    # Points mapping for different activity types
    points_map = {
        'login': 5,
        'create_case': 10,
        'update_case': 5,
        'create_document': 10,
        'research': 15,
        'create_contract': 10,
        'add_event': 5,
        'complete_profile': 20
    }
    
    points = points_map.get(activity_type, 1)
    
    # Record activity
    activity = Activity(
        user_id=current_user.id,
        activity_type=activity_type,
        description=description,
        points=points
    )
    db.session.add(activity)
    
    # Update user profile
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.session.add(profile)
    
    # Add points
    new_level = profile.add_points(points)
    level_up = new_level > profile.level
    
    # Update activity counters
    if activity_type == 'create_case':
        profile.total_cases_managed += 1
    elif activity_type == 'create_document':
        profile.total_documents_created += 1
    elif activity_type == 'research':
        profile.total_research_conducted += 1
    
    db.session.commit()
    
    # Check for new achievements
    new_achievements = check_achievements(current_user.id)
    
    return jsonify({
        'success': True,
        'points_earned': points,
        'new_total': profile.total_points,
        'level': profile.level,
        'level_up': level_up,
        'new_achievements': new_achievements
    })

def check_achievements(user_id):
    """Check if user has earned any new achievements"""
    # Get user profile
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return []
    
    # Get user's current achievements
    user_achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    earned_achievement_ids = [ua.achievement_id for ua in user_achievements]
    
    # Get all active achievements
    all_achievements = Achievement.query.filter_by(is_active=True).all()
    
    new_achievements = []
    
    for achievement in all_achievements:
        # Skip if already earned
        if achievement.id in earned_achievement_ids:
            continue
        
        # Get achievement requirements
        requirements = achievement.get_requirements()
        requirement_met = False
        
        # Check if requirements are met
        if 'min_level' in requirements and profile.level >= requirements['min_level']:
            requirement_met = True
        elif 'min_points' in requirements and profile.total_points >= requirements['min_points']:
            requirement_met = True
        elif 'min_streak' in requirements and profile.streak_days >= requirements['min_streak']:
            requirement_met = True
        elif 'min_cases' in requirements and profile.total_cases_managed >= requirements['min_cases']:
            requirement_met = True
        elif 'min_documents' in requirements and profile.total_documents_created >= requirements['min_documents']:
            requirement_met = True
        elif 'min_research' in requirements and profile.total_research_conducted >= requirements['min_research']:
            requirement_met = True
        
        if requirement_met:
            # Award achievement
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id
            )
            db.session.add(user_achievement)
            
            # Award points
            profile.add_points(achievement.points)
            
            # Record activity
            activity = Activity(
                user_id=user_id,
                activity_type='earn_achievement',
                description=f'Earned achievement: {achievement.name}',
                points=achievement.points
            )
            db.session.add(activity)
            
            # Add to new achievements list
            new_achievements.append({
                'id': achievement.id,
                'name': achievement.name,
                'description': achievement.description,
                'points': achievement.points,
                'icon': achievement.icon
            })
    
    if new_achievements:
        db.session.commit()
    
    return new_achievements