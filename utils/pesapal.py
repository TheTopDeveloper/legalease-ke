"""
Mock payment system for testing without API keys.
This will be replaced with PesaPal or DPO integration when API keys are available.
"""

import uuid
from datetime import datetime, timedelta
from flask import url_for

from app import db
from models import Payment, User, Subscription, TokenPackage

class MockPaymentSystem:
    """
    A mock payment system for testing without external payment gateways.
    This will be replaced with actual PesaPal or DPO integration when API keys are available.
    """
    
    def submit_order(self, user, amount, description, payment_type="subscription", redirect_url=None):
        """Create a new payment record and generate a mock payment page URL"""
        # Generate a unique transaction ID
        transaction_id = f"MOCK-{uuid.uuid4().hex[:10].upper()}"
        
        # Create payment record
        payment = Payment(
            user_id=user.id,
            amount=amount,
            payment_type=payment_type,
            payment_method='mock',
            transaction_id=transaction_id,
            status='pending',
            payment_data=description
        )
        
        db.session.add(payment)
        db.session.commit()
        
        # Return the mock payment URL
        return url_for('billing.mock_payment', transaction_id=transaction_id)
    
    def process_payment(self, transaction_id, status='completed'):
        """Process a payment with the given status"""
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        
        if not payment:
            return False
            
        payment.status = status
        
        if status == 'completed':
            payment.completed_at = datetime.utcnow()
            
            # Process subscription purchase
            if payment.payment_type == 'subscription' and payment.subscription_id:
                subscription = Subscription.query.get(payment.subscription_id)
                user = User.query.get(payment.user_id)
                
                if subscription and user:
                    # Update user's subscription
                    user.account_type = subscription.name
                    user.max_cases = subscription.max_cases
                    user.tokens_available += subscription.tokens_included
                    
                    # Set subscription end date
                    current_time = datetime.utcnow()
                    user.subscription_end = current_time + timedelta(days=subscription.duration_days)
            
            # Process token purchase
            elif payment.payment_type == 'tokens' and payment.token_package_id:
                token_package = TokenPackage.query.get(payment.token_package_id)
                user = User.query.get(payment.user_id)
                
                if token_package and user:
                    # Add tokens to user's account
                    user.tokens_available += token_package.token_count
        
        db.session.commit()
        return True

# Use this mock system for now, replace with real implementation later
payment_gateway = MockPaymentSystem()