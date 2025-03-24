"""
Initialize database with default subscription plans and token packages.
Run this script after setting up the database to add initial data.
"""

import os
import sys
from datetime import datetime
from app import app, db
from models import Subscription, TokenPackage

def create_subscription_plans():
    """Create default subscription plans"""
    # Check if plans already exist
    if Subscription.query.count() > 0:
        print("Subscription plans already exist. Skipping creation.")
        return

    # Create individual plans
    basic = Subscription(
        name='basic',
        price=2000.00,
        duration_days=30,
        max_cases=10,
        tokens_included=100,
        is_organization=False,
        max_users=1,
        is_active=True,
        features="Basic document generation|Legal research access|10 cases"
    )

    premium = Subscription(
        name='premium',
        price=4000.00,
        duration_days=30,
        max_cases=25,
        tokens_included=250,
        is_organization=False,
        max_users=1,
        is_active=True,
        features="Advanced document generation|Comprehensive legal research|Case analysis|Contract review|25 cases"
    )

    # Create organization plans
    organization_basic = Subscription(
        name='org_basic',
        price=10000.00,
        duration_days=30,
        max_cases=50,
        tokens_included=500,
        is_organization=True,
        max_users=5,
        is_active=True,
        features="Basic document generation|Legal research access|50 cases|5 users"
    )

    organization_premium = Subscription(
        name='org_premium',
        price=20000.00,
        duration_days=30,
        max_cases=100,
        tokens_included=1000,
        is_organization=True,
        max_users=10,
        is_active=True,
        features="Advanced document generation|Comprehensive legal research|Case analysis|Contract review|100 cases|10 users"
    )

    # Add plans to database
    db.session.add_all([basic, premium, organization_basic, organization_premium])
    db.session.commit()
    print("Created subscription plans: basic, premium, org_basic, org_premium")


def create_token_packages():
    """Create default token packages"""
    # Check if packages already exist
    if TokenPackage.query.count() > 0:
        print("Token packages already exist. Skipping creation.")
        return

    # Create token packages
    small = TokenPackage(
        name='Small Package',
        token_count=100,
        price=500.00,
        is_active=True
    )

    medium = TokenPackage(
        name='Medium Package',
        token_count=250,
        price=1000.00,
        is_active=True
    )

    large = TokenPackage(
        name='Large Package',
        token_count=500,
        price=1750.00,
        is_active=True
    )

    # Add packages to database
    db.session.add_all([small, medium, large])
    db.session.commit()
    print("Created token packages: Small, Medium, Large")


if __name__ == '__main__':
    with app.app_context():
        print("Initializing default subscription plans and token packages...")
        create_subscription_plans()
        create_token_packages()
        print("Initialization complete.")