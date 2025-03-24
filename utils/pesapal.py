import json
import secrets
import time
from datetime import datetime, timedelta
from flask import url_for

class MockPaymentSystem:
    """
    A mock payment system for testing without external payment gateways.
    This will be replaced with actual PesaPal or DPO integration when API keys are available.
    """
    
    def submit_order(self, user, amount, description, payment_type="subscription", redirect_url=None):
        """Create a new payment record and generate a mock payment page URL"""
        from app import db
        from models import Payment
        
        # Generate a unique transaction ID
        transaction_id = f"TRX-{int(time.time())}-{secrets.token_hex(4)}"
        
        # Mock payment data
        payment_data = {
            "order_tracking_id": transaction_id,
            "redirect_url": url_for('billing.mock_payment', transaction_id=transaction_id, _external=True)
        }
        
        # Save the payment record in the database
        payment = Payment(
            amount=amount,
            payment_type=payment_type,
            payment_method='manual',
            transaction_id=transaction_id,
            status='pending',
            payment_data=json.dumps(payment_data),
            user_id=user.id
        )
        
        if payment_type == 'subscription' and hasattr(user, 'selected_subscription_id'):
            payment.subscription_id = user.selected_subscription_id
            
        if payment_type == 'tokens' and hasattr(user, 'selected_token_package_id'):
            payment.token_package_id = user.selected_token_package_id
            
        db.session.add(payment)
        db.session.commit()
        
        # Return mock payment page URL
        return payment_data["redirect_url"], payment
    
    def process_payment(self, transaction_id, status='completed'):
        """Process a payment with the given status"""
        from app import db
        from models import Payment, User, Subscription, TokenPackage
        
        # Find payment by transaction_id
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        
        if not payment:
            return False, "Payment not found"
            
        # Update payment status
        payment.status = status
        
        if status == 'completed':
            payment.completed_at = datetime.now()
            
            user = User.query.get(payment.user_id)
            
            # Process subscription payment
            if payment.payment_type == 'subscription' and payment.subscription_id:
                subscription = Subscription.query.get(payment.subscription_id)
                if subscription:
                    user.account_type = subscription.name
                    user.max_cases = subscription.max_cases
                    user.tokens_available += subscription.tokens_included
                    user.subscription_end = datetime.now() + timedelta(days=subscription.duration_days)
            
            # Process token purchase
            if payment.payment_type == 'tokens' and payment.token_package_id:
                token_package = TokenPackage.query.get(payment.token_package_id)
                if token_package:
                    user.tokens_available += token_package.token_count
            
            db.session.commit()
            return True, "Payment processed successfully"
        
        elif status == 'failed':
            db.session.commit()
            return False, "Payment failed"
        
        else:
            # Payment still pending
            db.session.commit()
            return False, f"Payment in status: {status}"

# Use MockPaymentSystem as PesaPalPayment to maintain compatibility with existing code
PesaPalPayment = MockPaymentSystem