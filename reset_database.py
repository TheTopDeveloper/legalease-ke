"""
Reset and recreate the database with the correct schema.
Run this script when database schema needs to be updated.
"""

import os
from app import app, db, logger

# Drop and recreate tables
with app.app_context():
    logger.info("Dropping all database tables...")
    db.drop_all()
    logger.info("Creating database tables...")
    db.create_all()
    logger.info("Database reset complete.")

    # Run initial data load if needed
    from init_data import create_subscription_plans, create_token_packages
    try:
        logger.info("Creating default subscription plans...")
        create_subscription_plans()
        logger.info("Creating default token packages...")
        create_token_packages()
        logger.info("Initial data loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading initial data: {str(e)}")

if __name__ == "__main__":
    print("Database has been reset and recreated with the current schema.")
    print("Default subscription plans and token packages have been created.")