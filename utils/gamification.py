"""
Gamification utility functions for the legal platform.
Handles points, achievements, streaks, levels, and challenges.
"""

import json
import random
from datetime import datetime, timedelta

from app import db
from models import UserProfile, Activity, Achievement, UserAchievement, Challenge, UserChallenge

# Constants
POINTS_PER_LEVEL = 100
STREAK_THRESHOLDS = {
    3: 1,  # 3-day streak: +1 token bonus
    5: 2,  # 5-day streak: +2 token bonus
    7: 3   # 7-day streak: +3 token bonus
}
DAILY_REWARD_TOKENS = 2  # Base tokens for daily rewards

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
        profile = user.profile
        
        if not profile:
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
        from routes.gamification import ACTIVITY_POINTS
        
        # Get or create user profile
        profile = GamificationService.get_or_create_profile(user)
        
        # Determine points for activity
        points = ACTIVITY_POINTS.get(activity_type, 0)
        
        # Create activity record
        activity = Activity(
            user_id=user.id,
            activity_type=activity_type,
            description=description or f"{activity_type.replace('_', ' ').capitalize()}",
            points=points
        )
        db.session.add(activity)
        
        # Add points to profile
        old_level = profile.level
        profile.add_points(points)
        
        # Update streak for login activity
        if activity_type == 'login':
            profile.update_streak()
        
        # Update challenge progress
        GamificationService.update_challenge_progress(user, activity_type)
        
        # Check for new achievements
        new_achievements = GamificationService.check_achievements(user)
        
        # Create response
        result = {
            'points': points,
            'total_points': profile.total_points,
            'level': profile.level,
            'level_up': profile.level > old_level,
            'new_achievements': new_achievements
        }
        
        db.session.commit()
        return result
    
    @staticmethod
    def create_default_achievements():
        """
        Create default achievements if they don't exist
        """
        achievements = [
            {
                'name': 'First Login',
                'description': 'Logged in for the first time.',
                'category': 'general',
                'points': 10,
                'icon': 'fas fa-door-open',
                'requirement': json.dumps({'login_count': 1})
            },
            {
                'name': 'Legal Beginner',
                'description': 'Reached level 2.',
                'category': 'general',
                'points': 20,
                'icon': 'fas fa-graduation-cap',
                'requirement': json.dumps({'min_level': 2})
            },
            {
                'name': 'Point Collector',
                'description': 'Earned 500 points.',
                'category': 'general',
                'points': 25,
                'icon': 'fas fa-star',
                'requirement': json.dumps({'min_points': 500})
            },
            {
                'name': 'Case Handler',
                'description': 'Created your first case.',
                'category': 'case',
                'points': 15,
                'icon': 'fas fa-gavel',
                'requirement': json.dumps({'min_cases': 1})
            },
            {
                'name': 'Case Master',
                'description': 'Managed 10 cases.',
                'category': 'case',
                'points': 30,
                'icon': 'case_master.svg',
                'requirement': json.dumps({'min_cases': 10})
            },
            {
                'name': 'Documentalist',
                'description': 'Created your first document.',
                'category': 'document',
                'points': 15,
                'icon': 'fas fa-file-alt',
                'requirement': json.dumps({'min_documents': 1})
            },
            {
                'name': 'Legal Researcher',
                'description': 'Conducted your first research.',
                'category': 'research',
                'points': 15,
                'icon': 'fas fa-search',
                'requirement': json.dumps({'min_research': 1})
            },
            {
                'name': 'Legal Eagle',
                'description': 'Conducted 10 research sessions.',
                'category': 'research',
                'points': 30,
                'icon': 'legal_eagle.svg',
                'requirement': json.dumps({'min_research': 10})
            },
            {
                'name': 'Streak Master',
                'description': 'Maintained a 7-day login streak.',
                'category': 'general',
                'points': 50,
                'icon': 'streak_master.svg',
                'requirement': json.dumps({'min_streak': 7})
            }
        ]
        
        existing_achievements = {a.name: a for a in Achievement.query.all()}
        
        for achievement_data in achievements:
            name = achievement_data['name']
            if name not in existing_achievements:
                achievement = Achievement(**achievement_data)
                db.session.add(achievement)
                print(f"Added achievement: {name}")
        
        db.session.commit()
    
    @staticmethod
    def check_achievements(user):
        """
        Check if user qualifies for new achievements
        
        Args:
            user: User object
            
        Returns:
            List of new achievements earned
        """
        # Get user profile and stats
        profile = GamificationService.get_or_create_profile(user)
        stats = GamificationService.get_user_stats(user)
        
        # Get user's current achievements
        current_achievements = {ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user.id).all()}
        
        # Get all achievements
        all_achievements = Achievement.query.filter_by(is_active=True).all()
        
        new_achievements = []
        
        for achievement in all_achievements:
            # Skip if already earned
            if achievement.id in current_achievements:
                continue
                
            # Check if user meets requirements
            requirements = achievement.get_requirements()
            qualified = True
            
            # Check login count
            if 'login_count' in requirements and stats['login_count'] < requirements['login_count']:
                qualified = False
                
            # Check minimum level
            if 'min_level' in requirements and profile.level < requirements['min_level']:
                qualified = False
                
            # Check minimum points
            if 'min_points' in requirements and profile.total_points < requirements['min_points']:
                qualified = False
                
            # Check minimum cases
            if 'min_cases' in requirements and stats['total_cases'] < requirements['min_cases']:
                qualified = False
                
            # Check minimum documents
            if 'min_documents' in requirements and stats['total_documents'] < requirements['min_documents']:
                qualified = False
                
            # Check minimum research
            if 'min_research' in requirements and stats['total_research'] < requirements['min_research']:
                qualified = False
                
            # Check minimum streak
            if 'min_streak' in requirements and profile.streak_days < requirements['min_streak']:
                qualified = False
                
            # If qualified, award achievement
            if qualified:
                # Create user achievement
                user_achievement = UserAchievement(
                    user_id=user.id,
                    achievement_id=achievement.id
                )
                db.session.add(user_achievement)
                
                # Add achievement points
                profile.add_points(achievement.points)
                
                # Add to result list
                new_achievements.append({
                    'id': achievement.id,
                    'name': achievement.name,
                    'description': achievement.description,
                    'category': achievement.category,
                    'icon': achievement.icon,
                    'points': achievement.points
                })
        
        if new_achievements:
            db.session.commit()
            
        return new_achievements
    
    @staticmethod
    def create_daily_challenges():
        """
        Create daily challenges if there are none active
        """
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)
        
        # Check for existing active daily challenges
        active_daily = Challenge.query.filter(
            Challenge.challenge_type == 'daily',
            Challenge.end_date > now,
            Challenge.start_date <= now,
            Challenge.is_active == True
        ).first()
        
        if active_daily:
            return
            
        # Create new daily challenge
        daily_challenges = [
            {
                'title': 'Daily Login',
                'description': 'Log in to the platform today.',
                'challenge_type': 'daily',
                'points': 10,
                'requirements': json.dumps({'type': 'login', 'target': 1}),
            },
            {
                'title': 'Research Session',
                'description': 'Conduct one legal research session today.',
                'challenge_type': 'daily',
                'points': 15,
                'requirements': json.dumps({'type': 'research', 'target': 1}),
            },
            {
                'title': 'Case Update',
                'description': 'Update one of your cases today.',
                'challenge_type': 'daily',
                'points': 10,
                'requirements': json.dumps({'type': 'update_case', 'target': 1}),
            }
        ]
        
        # Randomly select one daily challenge
        challenge_data = random.choice(daily_challenges)
        challenge_data['start_date'] = now
        challenge_data['end_date'] = tomorrow
        challenge_data['is_active'] = True
        
        challenge = Challenge(**challenge_data)
        db.session.add(challenge)
        db.session.commit()
    
    @staticmethod
    def create_weekly_challenges():
        """
        Create weekly challenges if there are none active
        """
        now = datetime.utcnow()
        next_week = now + timedelta(days=7)
        
        # Check for existing active weekly challenges
        active_weekly = Challenge.query.filter(
            Challenge.challenge_type == 'weekly',
            Challenge.end_date > now,
            Challenge.start_date <= now,
            Challenge.is_active == True
        ).count()
        
        if active_weekly >= 2:  # We want at most 2 active weekly challenges
            return
            
        # Weekly challenge templates
        weekly_challenges = [
            {
                'title': 'Research Champion',
                'description': 'Conduct 3 legal research sessions in a week.',
                'challenge_type': 'weekly',
                'points': 50,
                'requirements': json.dumps({'type': 'research', 'target': 3}),
            },
            {
                'title': 'Document Master',
                'description': 'Create 2 legal documents in a week.',
                'challenge_type': 'weekly',
                'points': 40,
                'requirements': json.dumps({'type': 'create_document', 'target': 2}),
            },
            {
                'title': 'Case Manager',
                'description': 'Create or update 5 cases in a week.',
                'challenge_type': 'weekly',
                'points': 45,
                'requirements': json.dumps({'type': 'case_actions', 'target': 5}),
            }
        ]
        
        # Get existing challenge titles to avoid duplicates
        existing_titles = [c.title for c in Challenge.query.filter(
            Challenge.challenge_type == 'weekly',
            Challenge.end_date > now,
            Challenge.is_active == True
        ).all()]
        
        # Filter out existing challenges
        available_challenges = [c for c in weekly_challenges if c['title'] not in existing_titles]
        
        if not available_challenges:
            return
            
        # Create new weekly challenge
        num_to_create = 2 - active_weekly
        for _ in range(min(num_to_create, len(available_challenges))):
            challenge_data = available_challenges.pop(0)
            challenge_data['start_date'] = now
            challenge_data['end_date'] = next_week
            challenge_data['is_active'] = True
            
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
        # Ensure daily and weekly challenges exist
        GamificationService.create_daily_challenges()
        GamificationService.create_weekly_challenges()
        
        now = datetime.utcnow()
        
        # Get active challenges
        active_challenges = Challenge.query.filter(
            Challenge.end_date > now,
            Challenge.start_date <= now,
            Challenge.is_active == True
        ).all()
        
        result = []
        
        for challenge in active_challenges:
            # Check if user has accepted this challenge
            user_challenge = UserChallenge.query.filter_by(
                user_id=user.id,
                challenge_id=challenge.id
            ).first()
            
            # If not, create a new user challenge
            if not user_challenge:
                user_challenge = UserChallenge(
                    user_id=user.id,
                    challenge_id=challenge.id,
                    status='accepted',
                    progress=json.dumps({'progress': 0})
                )
                db.session.add(user_challenge)
                db.session.commit()
            
            # Get requirements and progress
            requirements = challenge.get_requirements()
            progress_data = user_challenge.get_progress()
            
            # Calculate progress percentage
            target = requirements.get('target', 1)
            progress = progress_data.get('progress', 0)
            progress_percentage = min(int(progress / target * 100), 100)
            
            # Add to result
            result.append({
                'id': challenge.id,
                'title': challenge.title,
                'description': challenge.description,
                'challenge_type': challenge.challenge_type,
                'points': challenge.points,
                'status': user_challenge.status,
                'target': target,
                'progress': progress,
                'progress_percentage': progress_percentage,
                'start_date': challenge.start_date,
                'end_date': challenge.end_date
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
        user_challenges = UserChallenge.query.filter_by(
            user_id=user.id,
            status='accepted'
        ).all()
        
        for user_challenge in user_challenges:
            challenge = user_challenge.challenge
            
            # Skip if challenge is not active
            if not challenge.is_ongoing():
                continue
                
            # Get challenge requirements
            requirements = challenge.get_requirements()
            challenge_type = requirements.get('type')
            
            # Skip if activity type doesn't match challenge type
            if challenge_type == 'case_actions' and activity_type not in ['create_case', 'update_case']:
                continue
            elif challenge_type != 'case_actions' and challenge_type != activity_type:
                continue
                
            # Update progress
            progress_data = user_challenge.get_progress()
            current_progress = progress_data.get('progress', 0)
            target = requirements.get('target', 1)
            
            # Increment progress
            current_progress += 1
            progress_data['progress'] = current_progress
            user_challenge.progress = json.dumps(progress_data)
            
            # Check if challenge completed
            if current_progress >= target and user_challenge.status == 'accepted':
                user_challenge.status = 'completed'
                user_challenge.completed_at = datetime.utcnow()
                
                # Award challenge points
                profile = GamificationService.get_or_create_profile(user)
                profile.add_points(challenge.points)
                
                # Record activity
                activity = Activity(
                    user_id=user.id,
                    activity_type='complete_challenge',
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
        # Login count
        login_count = Activity.query.filter_by(user_id=user.id, activity_type='login').count()
        
        # Case stats
        total_cases = user.cases.count()
        case_creates = Activity.query.filter_by(user_id=user.id, activity_type='create_case').count()
        case_updates = Activity.query.filter_by(user_id=user.id, activity_type='update_case').count()
        
        # Document stats
        total_documents = user.documents.count()
        
        # Research stats
        total_research = Activity.query.filter_by(user_id=user.id, activity_type='research').count()
        
        return {
            'login_count': login_count,
            'total_cases': total_cases,
            'case_creates': case_creates,
            'case_updates': case_updates,
            'total_documents': total_documents,
            'total_research': total_research
        }