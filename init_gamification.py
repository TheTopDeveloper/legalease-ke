"""
Initialize database with default gamification achievements and challenges.
Run this script after setting up the database to add initial data.
"""

import os
import sys
import json
from datetime import datetime, timedelta

from app import app, db
from models import Achievement, Challenge
from utils.gamification import GamificationService

def create_achievements():
    """Create default achievements"""
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
    count = 0
    
    for achievement_data in achievements:
        name = achievement_data['name']
        if name not in existing_achievements:
            achievement = Achievement(**achievement_data)
            db.session.add(achievement)
            count += 1
            print(f"Added achievement: {name}")
    
    db.session.commit()
    print(f"Created {count} new achievements")

def create_challenges():
    """Create default challenges"""
    now = datetime.utcnow()
    tomorrow = now + timedelta(days=1)
    next_week = now + timedelta(days=7)
    
    # Daily challenges
    daily_challenges = [
        {
            'title': 'Daily Login',
            'description': 'Log in to the platform today.',
            'challenge_type': 'daily',
            'points': 10,
            'requirements': json.dumps({'type': 'login', 'target': 1}),
            'start_date': now,
            'end_date': tomorrow,
            'is_active': True
        },
        {
            'title': 'Research Session',
            'description': 'Conduct one legal research session today.',
            'challenge_type': 'daily',
            'points': 15,
            'requirements': json.dumps({'type': 'research', 'target': 1}),
            'start_date': now,
            'end_date': tomorrow,
            'is_active': True
        }
    ]
    
    # Weekly challenges
    weekly_challenges = [
        {
            'title': 'Research Champion',
            'description': 'Conduct 3 legal research sessions in a week.',
            'challenge_type': 'weekly',
            'points': 50,
            'requirements': json.dumps({'type': 'research', 'target': 3}),
            'start_date': now,
            'end_date': next_week,
            'is_active': True
        },
        {
            'title': 'Document Master',
            'description': 'Create 2 legal documents in a week.',
            'challenge_type': 'weekly',
            'points': 40,
            'requirements': json.dumps({'type': 'create_document', 'target': 2}),
            'start_date': now,
            'end_date': next_week,
            'is_active': True
        }
    ]
    
    # First check if we already have active challenges
    active_daily = Challenge.query.filter(
        Challenge.challenge_type == 'daily',
        Challenge.end_date > now,
        Challenge.is_active == True
    ).first()
    
    active_weekly = Challenge.query.filter(
        Challenge.challenge_type == 'weekly',
        Challenge.end_date > now,
        Challenge.is_active == True
    ).count()
    
    count = 0
    
    # Only add daily if we don't have one
    if not active_daily:
        # Add one random daily challenge
        import random
        challenge_data = random.choice(daily_challenges)
        challenge = Challenge(**challenge_data)
        db.session.add(challenge)
        count += 1
        print(f"Added daily challenge: {challenge_data['title']}")
    
    # Only add weekly if we don't have at least 2
    if active_weekly < 2:
        num_to_add = 2 - active_weekly
        for i in range(min(num_to_add, len(weekly_challenges))):
            challenge_data = weekly_challenges[i]
            challenge = Challenge(**challenge_data)
            db.session.add(challenge)
            count += 1
            print(f"Added weekly challenge: {challenge_data['title']}")
    
    db.session.commit()
    print(f"Created {count} new challenges")

def main():
    """Main function to initialize gamification data"""
    with app.app_context():
        print("Creating achievements...")
        create_achievements()
        
        print("\nCreating challenges...")
        create_challenges()
        
        print("\nGamification data initialization complete!")

if __name__ == "__main__":
    main()