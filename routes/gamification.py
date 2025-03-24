from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import User, UserProfile, Achievement, UserAchievement, Activity, Challenge, UserChallenge

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
    user_achievements = db.session.query(UserAchievement, Achievement).join(
        Achievement, UserAchievement.achievement_id == Achievement.id
    ).filter(UserAchievement.user_id == current_user.id).all()
    
    # Format user achievements for display
    recent_achievements = []
    for ua, achievement in user_achievements[:6]:  # Get most recent 6
        achievement_data = {
            'id': achievement.id,
            'name': achievement.name,
            'description': achievement.description,
            'icon': achievement.icon,
            'points': achievement.points,
            'category': achievement.category,
            'earned': True,
            'earned_at': ua.earned_at
        }
        recent_achievements.append(achievement_data)
    
    # If we don't have enough earned achievements, add some unearned ones
    earned_ids = [ua.achievement_id for ua, _ in user_achievements]
    if len(recent_achievements) < 6:
        unearned = Achievement.query.filter(
            ~Achievement.id.in_(earned_ids), 
            Achievement.is_active == True
        ).limit(6 - len(recent_achievements)).all()
        
        for achievement in unearned:
            achievement_data = {
                'id': achievement.id,
                'name': achievement.name,
                'description': achievement.description,
                'icon': achievement.icon,
                'points': achievement.points,
                'category': achievement.category,
                'earned': False
            }
            recent_achievements.append(achievement_data)
    
    # Get active challenges
    active_challenges = Challenge.query.filter(
        Challenge.is_active == True,
        Challenge.start_date <= datetime.utcnow(),
        Challenge.end_date >= datetime.utcnow()
    ).order_by(Challenge.end_date).limit(6).all()
    
    # Get user's active challenges
    user_challenges = UserChallenge.query.filter_by(
        user_id=current_user.id,
        status='accepted'
    ).all()
    user_challenge_dict = {uc.challenge_id: uc for uc in user_challenges}
    
    # Format challenges for display
    challenge_data = []
    for challenge in active_challenges:
        days_remaining = (challenge.end_date - datetime.utcnow()).days + 1
        
        challenge_dict = {
            'id': challenge.id,
            'title': challenge.title,
            'description': challenge.description,
            'points': challenge.points,
            'challenge_type': challenge.challenge_type,
            'start_date': challenge.start_date,
            'end_date': challenge.end_date,
            'days_remaining': days_remaining,
            'is_active': challenge.is_active,
            'accepted': False,
            'status': 'available'
        }
        
        # If user has accepted this challenge
        if challenge.id in user_challenge_dict:
            user_challenge = user_challenge_dict[challenge.id]
            challenge_dict['accepted'] = True
            challenge_dict['status'] = user_challenge.status
            
            # Get progress if available
            if user_challenge.progress:
                progress = user_challenge.get_progress()
                target = 1  # Default target
                
                # Get target from requirements
                requirements = challenge.get_requirements()
                if requirements and 'target' in requirements:
                    target = requirements['target']
                
                current = progress.get('progress', 0)
                challenge_dict['current_progress'] = current
                challenge_dict['target_progress'] = target
                challenge_dict['progress_percentage'] = min(int((current / target) * 100), 100)
        
        challenge_data.append(challenge_dict)
    
    # Calculate progress to next level
    next_level_points = (profile.level * 100)
    current_level_points = ((profile.level - 1) * 100)
    level_progress = round(((profile.total_points - current_level_points) / 
                           (next_level_points - current_level_points) * 100), 1)
    
    # User stats for dashboard
    user_stats = {
        'level': profile.level,
        'title': profile.title,
        'total_points': profile.total_points,
        'streak_days': profile.streak_days,
        'last_active': profile.last_active,
        'total_cases_managed': profile.total_cases_managed,
        'total_documents_created': profile.total_documents_created,
        'total_research_conducted': profile.total_research_conducted,
        'level_progress': level_progress,
        'points_to_next_level': next_level_points - profile.total_points,
        'achievements_earned': len(earned_ids),
        'total_achievements': Achievement.query.filter_by(is_active=True).count()
    }
    
    return render_template(
        'gamification/dashboard.html',
        user_stats=user_stats,
        recent_achievements=recent_achievements,
        active_challenges=challenge_data
    )

@gamification_bp.route('/achievements')
@login_required
def achievements():
    """View all achievements in the system"""
    # Get user achievements with full achievement data
    user_achievements = db.session.query(UserAchievement, Achievement).join(
        Achievement, UserAchievement.achievement_id == Achievement.id
    ).filter(UserAchievement.user_id == current_user.id).all()
    
    # Format user achievements for template
    formatted_user_achievements = []
    for ua, achievement in user_achievements:
        achievement_dict = {
            'id': achievement.id,
            'name': achievement.name,
            'description': achievement.description,
            'icon': achievement.icon,
            'points': achievement.points,
            'category': achievement.category,
            'earned_at': ua.earned_at
        }
        
        # Add category color
        if achievement.category == 'case':
            achievement_dict['category_color'] = 'primary'
        elif achievement.category == 'document':
            achievement_dict['category_color'] = 'info'
        elif achievement.category == 'research':
            achievement_dict['category_color'] = 'warning'
        else:
            achievement_dict['category_color'] = 'secondary'
            
        formatted_user_achievements.append(achievement_dict)
    
    # Get all achievements
    all_achievements = Achievement.query.filter_by(is_active=True).all()
    formatted_all_achievements = []
    
    earned_achievement_ids = [ua.achievement_id for ua, _ in user_achievements]
    
    for achievement in all_achievements:
        achievement_dict = {
            'id': achievement.id,
            'name': achievement.name,
            'description': achievement.description,
            'icon': achievement.icon,
            'points': achievement.points,
            'category': achievement.category,
            'earned': achievement.id in earned_achievement_ids
        }
        
        # Add category color
        if achievement.category == 'case':
            achievement_dict['category_color'] = 'primary'
        elif achievement.category == 'document':
            achievement_dict['category_color'] = 'info'
        elif achievement.category == 'research':
            achievement_dict['category_color'] = 'warning'
        else:
            achievement_dict['category_color'] = 'secondary'
            
        formatted_all_achievements.append(achievement_dict)
    
    return render_template(
        'gamification/achievements.html',
        user_achievements=formatted_user_achievements,
        all_achievements=formatted_all_achievements
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
    
    # Get all user challenges (including completed ones)
    user_challenges = UserChallenge.query.filter_by(user_id=current_user.id).all()
    user_challenge_dict = {uc.challenge_id: uc for uc in user_challenges}
    
    # Get some completed challenges to show history
    completed_challenges = Challenge.query.join(
        UserChallenge, Challenge.id == UserChallenge.challenge_id
    ).filter(
        UserChallenge.user_id == current_user.id,
        UserChallenge.status == 'completed'
    ).order_by(UserChallenge.completed_at.desc()).limit(3).all()
    
    # Format all challenges (active + completed)
    all_challenges = []
    
    # Process active challenges
    for challenge in active_challenges:
        days_remaining = (challenge.end_date - datetime.utcnow()).days + 1
        
        challenge_dict = {
            'id': challenge.id,
            'title': challenge.title,
            'description': challenge.description,
            'points': challenge.points,
            'challenge_type': challenge.challenge_type,
            'start_date': challenge.start_date,
            'end_date': challenge.end_date,
            'days_remaining': days_remaining,
            'is_active': challenge.is_active,
            'status': 'available'
        }
        
        # If user has accepted or completed this challenge
        if challenge.id in user_challenge_dict:
            user_challenge = user_challenge_dict[challenge.id]
            challenge_dict['status'] = user_challenge.status
            
            # Get progress if available
            if user_challenge.progress:
                progress = user_challenge.get_progress()
                target = 1  # Default target
                
                # Get target from requirements
                requirements = challenge.get_requirements()
                if requirements and 'target' in requirements:
                    target = requirements['target']
                
                current = progress.get('progress', 0)
                challenge_dict['current_progress'] = current
                challenge_dict['target_progress'] = target
                challenge_dict['progress_percentage'] = min(int((current / target) * 100), 100)
                
            # Add completion date if completed
            if user_challenge.status == 'completed' and user_challenge.completed_at:
                challenge_dict['completed_at'] = user_challenge.completed_at
        
        all_challenges.append(challenge_dict)
    
    # Process completed challenges (that aren't active anymore)
    for challenge in completed_challenges:
        # Skip if already added (it's still active)
        if challenge.id in [c.get('id') for c in all_challenges]:
            continue
            
        user_challenge = user_challenge_dict.get(challenge.id)
        if not user_challenge:
            continue
            
        challenge_dict = {
            'id': challenge.id,
            'title': challenge.title,
            'description': challenge.description,
            'points': challenge.points,
            'challenge_type': challenge.challenge_type,
            'start_date': challenge.start_date,
            'end_date': challenge.end_date,
            'is_active': False,
            'status': 'completed',
            'completed_at': user_challenge.completed_at
        }
        
        all_challenges.append(challenge_dict)
    
    return render_template(
        'gamification/challenges.html',
        challenges=all_challenges
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
    # Get all users with their profiles for the leaderboard
    all_users = db.session.query(
        UserProfile, User
    ).join(
        User, UserProfile.user_id == User.id
    ).order_by(
        UserProfile.total_points.desc()
    ).all()
    
    # Format users for the leaderboard
    formatted_users = []
    for profile, user in all_users:
        # Count achievements
        achievement_count = UserAchievement.query.filter_by(user_id=user.id).count()
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'level': profile.level,
            'title': profile.title,
            'total_points': profile.total_points,
            'streak_days': profile.streak_days,
            'achievements_count': achievement_count
        }
        formatted_users.append(user_data)
    
    # Get current user's stats
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    if not user_profile:
        # Create profile if it doesn't exist
        user_profile = UserProfile(user_id=current_user.id)
        db.session.add(user_profile)
        db.session.commit()
    
    # Get user achievements count
    achievements_earned = UserAchievement.query.filter_by(user_id=current_user.id).count()
    
    # Current user stats for the profile card
    current_user_stats = {
        'level': user_profile.level,
        'title': user_profile.title,
        'total_points': user_profile.total_points,
        'achievements_earned': achievements_earned
    }
    
    # Calculate user's rank
    user_rank = 1
    points_to_next_rank = 0
    
    if formatted_users:
        for idx, user_data in enumerate(formatted_users):
            if user_data['id'] == current_user.id:
                user_rank = idx + 1
                
                # Calculate points needed to reach next rank
                if idx > 0:  # Not already #1
                    next_rank_user = formatted_users[idx - 1]
                    points_to_next_rank = next_rank_user['total_points'] - user_data['total_points'] + 1
                break
    
    return render_template(
        'gamification/leaderboard.html',
        all_users=formatted_users,
        top_users=formatted_users[:3] if len(formatted_users) >= 3 else formatted_users,
        current_user_stats=current_user_stats,
        current_user_rank=user_rank,
        points_to_next_rank=points_to_next_rank
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