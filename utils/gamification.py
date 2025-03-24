"""
Gamification utility functions for the legal platform.
Handles points, achievements, streaks, levels, and challenges.
"""
from datetime import datetime
import json

from app import db
from models import User, UserProfile, Achievement, UserAchievement, Activity, Challenge, UserChallenge

# Point values for different activities
POINTS = {
    'login': 1,
    'create_case': 10,
    'update_case': 3,
    'create_document': 8,
    'update_document': 2,
    'create_contract': 15,
    'update_contract': 5,
    'conduct_research': 10,
    'complete_profile': 5,
    'add_client': 5,
    'schedule_event': 3,
    'streak_milestone': 10  # additional points for streak milestones (3, 7, 14, 30 days)
}

# Activity types that count towards challenges and achievements
ACTIVITY_CATEGORIES = {
    'case': ['create_case', 'update_case'],
    'document': ['create_document', 'update_document'],
    'contract': ['create_contract', 'update_contract'],
    'research': ['conduct_research'],
    'client': ['add_client'],
    'event': ['schedule_event'],
    'profile': ['complete_profile', 'login'],
}

class GamificationService:
    """
    Service for handling gamification features in the application
    """
    
    @staticmethod
    def get_or_create_profile(user):
        """
        Get user profile or create if it doesn't exist
        
        Args:
            user: User object
            
        Returns:
            UserProfile object
        """
        if hasattr(user, 'profile') and user.profile:
            return user.profile
        
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
        return profile
    
    @staticmethod
    def record_activity(user, activity_type, description=None):
        """
        Record user activity and award points
        
        Args:
            user: User object
            activity_type: Type of activity (e.g., 'login', 'create_case')
            description: Optional description of the activity
            
        Returns:
            Dictionary with points earned and new level if applicable
        """
        if activity_type not in POINTS:
            return {'points': 0}
        
        # Get profile
        profile = GamificationService.get_or_create_profile(user)
        
        # Update streak for login activity
        if activity_type == 'login':
            profile.update_streak()
            
            # Award extra points for streak milestones
            streak_bonus = 0
            if profile.streak_days in [3, 7, 14, 30, 60, 90, 180, 365]:
                streak_bonus = POINTS['streak_milestone']
                streak_description = f"Achieved {profile.streak_days}-day login streak"
                streak_activity = Activity(
                    user_id=user.id,
                    activity_type='streak_milestone',
                    description=streak_description,
                    points=streak_bonus
                )
                db.session.add(streak_activity)
        
        # Record activity
        points = POINTS[activity_type]
        activity = Activity(
            user_id=user.id,
            activity_type=activity_type,
            description=description,
            points=points
        )
        db.session.add(activity)
        
        # Update counters based on activity type
        if activity_type == 'create_case':
            profile.total_cases_managed += 1
        elif activity_type == 'create_document':
            profile.total_documents_created += 1
        elif activity_type == 'conduct_research':
            profile.total_research_conducted += 1
        
        # Add points to profile
        old_level = profile.level
        new_level = profile.add_points(points + streak_bonus)
        
        # Save changes
        db.session.commit()
        
        # Check for achievements
        GamificationService.check_achievements(user)
        
        # Check for active challenges
        GamificationService.update_challenge_progress(user, activity_type)
        
        result = {
            'points': points + streak_bonus,
            'total_points': profile.total_points,
            'streak_days': profile.streak_days,
        }
        
        # Add level up notification if applicable
        if new_level > old_level:
            result['level_up'] = {
                'new_level': new_level,
                'new_title': profile.title
            }
        
        return result
    
    @staticmethod
    def create_default_achievements():
        """
        Create default achievements if they don't exist
        """
        default_achievements = [
            {
                'name': 'First Case',
                'description': 'Created your first legal case',
                'category': 'case',
                'points': 10,
                'icon': 'bi bi-briefcase',
                'requirement': json.dumps({'activity': 'create_case', 'count': 1})
            },
            {
                'name': 'Case Manager',
                'description': 'Created 10 legal cases',
                'category': 'case',
                'points': 30,
                'icon': 'bi bi-briefcase-fill',
                'requirement': json.dumps({'activity': 'create_case', 'count': 10})
            },
            {
                'name': 'Document Creator',
                'description': 'Created your first legal document',
                'category': 'document',
                'points': 10,
                'icon': 'bi bi-file-text',
                'requirement': json.dumps({'activity': 'create_document', 'count': 1})
            },
            {
                'name': 'Document Expert',
                'description': 'Created 20 legal documents',
                'category': 'document',
                'points': 40,
                'icon': 'bi bi-file-text-fill',
                'requirement': json.dumps({'activity': 'create_document', 'count': 20})
            },
            {
                'name': 'Contract Drafter',
                'description': 'Created your first contract',
                'category': 'contract',
                'points': 15,
                'icon': 'bi bi-file-earmark-text',
                'requirement': json.dumps({'activity': 'create_contract', 'count': 1})
            },
            {
                'name': 'Research Novice',
                'description': 'Conducted your first legal research',
                'category': 'research',
                'points': 10,
                'icon': 'bi bi-search',
                'requirement': json.dumps({'activity': 'conduct_research', 'count': 1})
            },
            {
                'name': 'Research Scholar',
                'description': 'Conducted 15 legal research sessions',
                'category': 'research',
                'points': 30,
                'icon': 'bi bi-search',
                'requirement': json.dumps({'activity': 'conduct_research', 'count': 15})
            },
            {
                'name': 'Active User',
                'description': 'Logged in for 3 consecutive days',
                'category': 'general',
                'points': 5,
                'icon': 'bi bi-calendar-check',
                'requirement': json.dumps({'streak': 3})
            },
            {
                'name': 'Dedicated User',
                'description': 'Logged in for 7 consecutive days',
                'category': 'general',
                'points': 10,
                'icon': 'bi bi-calendar-check-fill',
                'requirement': json.dumps({'streak': 7})
            },
            {
                'name': 'Committed User',
                'description': 'Logged in for 30 consecutive days',
                'category': 'general',
                'points': 50,
                'icon': 'bi bi-trophy',
                'requirement': json.dumps({'streak': 30})
            },
            {
                'name': 'Client Networker',
                'description': 'Added 5 clients to the system',
                'category': 'client',
                'points': 20,
                'icon': 'bi bi-people',
                'requirement': json.dumps({'activity': 'add_client', 'count': 5})
            },
            {
                'name': 'Organized Advocate',
                'description': 'Scheduled 10 events in the calendar',
                'category': 'event',
                'points': 20,
                'icon': 'bi bi-calendar-event',
                'requirement': json.dumps({'activity': 'schedule_event', 'count': 10})
            },
        ]
        
        for achievement_data in default_achievements:
            # Check if achievement already exists
            existing = Achievement.query.filter_by(name=achievement_data['name']).first()
            if not existing:
                achievement = Achievement(**achievement_data)
                db.session.add(achievement)
        
        db.session.commit()
    
    @staticmethod
    def check_achievements(user):
        """
        Check if user qualifies for new achievements
        
        Args:
            user: User object
        """
        profile = GamificationService.get_or_create_profile(user)
        
        # Get all achievements
        achievements = Achievement.query.filter_by(is_active=True).all()
        
        for achievement in achievements:
            # Skip if user already has this achievement
            if UserAchievement.query.filter_by(
                user_id=user.id, achievement_id=achievement.id
            ).first():
                continue
            
            requirements = achievement.get_requirements()
            
            # Check streak achievements
            if 'streak' in requirements and profile.streak_days >= requirements['streak']:
                user_achievement = UserAchievement(
                    user_id=user.id,
                    achievement_id=achievement.id
                )
                db.session.add(user_achievement)
                profile.add_points(achievement.points)
                
                # Record achievement activity
                activity = Activity(
                    user_id=user.id,
                    activity_type='achievement_earned',
                    description=f"Earned achievement: {achievement.name}",
                    points=achievement.points
                )
                db.session.add(activity)
                continue
            
            # Check activity count achievements
            if 'activity' in requirements and 'count' in requirements:
                activity_type = requirements['activity']
                required_count = requirements['count']
                
                # Count activities
                activity_count = Activity.query.filter_by(
                    user_id=user.id, activity_type=activity_type
                ).count()
                
                if activity_count >= required_count:
                    user_achievement = UserAchievement(
                        user_id=user.id,
                        achievement_id=achievement.id
                    )
                    db.session.add(user_achievement)
                    profile.add_points(achievement.points)
                    
                    # Record achievement activity
                    activity = Activity(
                        user_id=user.id,
                        activity_type='achievement_earned',
                        description=f"Earned achievement: {achievement.name}",
                        points=achievement.points
                    )
                    db.session.add(activity)
        
        db.session.commit()
    
    @staticmethod
    def create_daily_challenges():
        """
        Create daily challenges if there are none active
        """
        now = datetime.utcnow()
        
        # Check if there are active daily challenges
        active_challenges = Challenge.query.filter(
            Challenge.challenge_type == 'daily',
            Challenge.end_date > now,
            Challenge.is_active == True
        ).count()
        
        if active_challenges == 0:
            # Create new daily challenges
            daily_challenges = [
                {
                    'title': 'Daily Login',
                    'description': 'Login to the platform today',
                    'challenge_type': 'daily',
                    'points': 5,
                    'requirements': json.dumps({'activity': 'login', 'count': 1}),
                    'start_date': now,
                    'end_date': datetime(now.year, now.month, now.day, 23, 59, 59),
                    'is_active': True
                },
                {
                    'title': 'Case Update',
                    'description': 'Update at least one case today',
                    'challenge_type': 'daily',
                    'points': 10,
                    'requirements': json.dumps({'activity': 'update_case', 'count': 1}),
                    'start_date': now,
                    'end_date': datetime(now.year, now.month, now.day, 23, 59, 59),
                    'is_active': True
                },
                {
                    'title': 'Document Work',
                    'description': 'Create or update a legal document today',
                    'challenge_type': 'daily',
                    'points': 10,
                    'requirements': json.dumps({'activity': ['create_document', 'update_document'], 'count': 1}),
                    'start_date': now,
                    'end_date': datetime(now.year, now.month, now.day, 23, 59, 59),
                    'is_active': True
                }
            ]
            
            for challenge_data in daily_challenges:
                challenge = Challenge(**challenge_data)
                db.session.add(challenge)
            
            db.session.commit()
    
    @staticmethod
    def create_weekly_challenges():
        """
        Create weekly challenges if there are none active
        """
        now = datetime.utcnow()
        
        # Check if there are active weekly challenges
        active_challenges = Challenge.query.filter(
            Challenge.challenge_type == 'weekly',
            Challenge.end_date > now,
            Challenge.is_active == True
        ).count()
        
        if active_challenges == 0:
            # Calculate the end of the week (Sunday 23:59:59)
            days_until_sunday = 6 - now.weekday()
            if days_until_sunday < 0:
                days_until_sunday += 7
            
            end_of_week = datetime(
                now.year, now.month, now.day + days_until_sunday, 23, 59, 59
            )
            
            # Create new weekly challenges
            weekly_challenges = [
                {
                    'title': 'Productive Week',
                    'description': 'Create or update 5 legal cases this week',
                    'challenge_type': 'weekly',
                    'points': 30,
                    'requirements': json.dumps({'activity': ['create_case', 'update_case'], 'count': 5}),
                    'start_date': now,
                    'end_date': end_of_week,
                    'is_active': True
                },
                {
                    'title': 'Research Master',
                    'description': 'Conduct 3 legal research sessions this week',
                    'challenge_type': 'weekly',
                    'points': 25,
                    'requirements': json.dumps({'activity': 'conduct_research', 'count': 3}),
                    'start_date': now,
                    'end_date': end_of_week,
                    'is_active': True
                },
                {
                    'title': 'Documentation Expert',
                    'description': 'Create 3 legal documents this week',
                    'challenge_type': 'weekly',
                    'points': 25,
                    'requirements': json.dumps({'activity': 'create_document', 'count': 3}),
                    'start_date': now,
                    'end_date': end_of_week,
                    'is_active': True
                }
            ]
            
            for challenge_data in weekly_challenges:
                challenge = Challenge(**challenge_data)
                db.session.add(challenge)
            
            db.session.commit()
    
    @staticmethod
    def get_active_challenges(user):
        """
        Get active challenges for the user
        
        Args:
            user: User object
            
        Returns:
            List of active challenges with user progress
        """
        now = datetime.utcnow()
        
        # Get active challenges
        challenges = Challenge.query.filter(
            Challenge.end_date > now,
            Challenge.is_active == True
        ).all()
        
        result = []
        for challenge in challenges:
            # Check if user already accepted this challenge
            user_challenge = UserChallenge.query.filter_by(
                user_id=user.id, challenge_id=challenge.id
            ).first()
            
            # If not, create a new user challenge
            if not user_challenge:
                user_challenge = UserChallenge(
                    user_id=user.id,
                    challenge_id=challenge.id,
                    status='accepted',
                    progress=json.dumps({'activities': {}})
                )
                db.session.add(user_challenge)
                db.session.commit()
            
            # Get progress
            progress = user_challenge.get_progress()
            requirements = challenge.get_requirements()
            
            # Calculate completion percentage
            completion = 0
            if 'activity' in requirements and 'count' in requirements:
                required_count = requirements['count']
                activities = requirements['activity']
                
                if isinstance(activities, str):
                    activities = [activities]
                
                current_count = 0
                for activity in activities:
                    current_count += progress.get('activities', {}).get(activity, 0)
                
                completion = min(100, int((current_count / required_count) * 100))
            
            result.append({
                'challenge': challenge,
                'user_challenge': user_challenge,
                'completion': completion,
                'status': user_challenge.status
            })
        
        return result
    
    @staticmethod
    def update_challenge_progress(user, activity_type):
        """
        Update progress for active challenges
        
        Args:
            user: User object
            activity_type: Type of activity
        """
        # Get user's active challenges
        user_challenges = UserChallenge.query.join(Challenge).filter(
            UserChallenge.user_id == user.id,
            UserChallenge.status == 'accepted',
            Challenge.end_date > datetime.utcnow(),
            Challenge.is_active == True
        ).all()
        
        for user_challenge in user_challenges:
            challenge = user_challenge.challenge
            requirements = challenge.get_requirements()
            
            # Check if this activity is relevant for the challenge
            if 'activity' in requirements:
                activities = requirements['activity']
                if isinstance(activities, str):
                    activities = [activities]
                
                if activity_type in activities:
                    # Update progress
                    progress = user_challenge.get_progress()
                    if 'activities' not in progress:
                        progress['activities'] = {}
                    
                    if activity_type not in progress['activities']:
                        progress['activities'][activity_type] = 0
                    
                    progress['activities'][activity_type] += 1
                    user_challenge.progress = json.dumps(progress)
                    
                    # Check if challenge is completed
                    required_count = requirements.get('count', 1)
                    current_count = 0
                    
                    for activity in activities:
                        current_count += progress.get('activities', {}).get(activity, 0)
                    
                    if current_count >= required_count:
                        user_challenge.status = 'completed'
                        user_challenge.completed_at = datetime.utcnow()
                        
                        # Award points
                        profile = GamificationService.get_or_create_profile(user)
                        profile.add_points(challenge.points)
                        
                        # Record activity
                        activity = Activity(
                            user_id=user.id,
                            activity_type='challenge_completed',
                            description=f"Completed challenge: {challenge.title}",
                            points=challenge.points
                        )
                        db.session.add(activity)
        
        db.session.commit()
    
    @staticmethod
    def get_user_stats(user):
        """
        Get gamification stats for a user
        
        Args:
            user: User object
            
        Returns:
            Dictionary of user stats
        """
        profile = GamificationService.get_or_create_profile(user)
        
        # Get achievements
        achievements = UserAchievement.query.filter_by(user_id=user.id).all()
        achievement_count = len(achievements)
        
        # Get completed challenges
        completed_challenges = UserChallenge.query.filter_by(
            user_id=user.id, status='completed'
        ).count()
        
        # Get recent activities
        recent_activities = Activity.query.filter_by(user_id=user.id).order_by(
            Activity.created_at.desc()
        ).limit(10).all()
        
        # Calculate level progress
        next_level = profile.level + 1
        points_for_next_level = next_level * 100
        points_from_current_level = (profile.level - 1) * 100
        current_level_points = profile.total_points - points_from_current_level
        level_progress = int((current_level_points / 100) * 100)
        
        return {
            'profile': profile,
            'achievement_count': achievement_count,
            'completed_challenges': completed_challenges,
            'recent_activities': recent_activities,
            'level_progress': level_progress,
            'next_level_at': points_for_next_level,
            'points_needed': points_for_next_level - profile.total_points
        }