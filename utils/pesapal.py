import json
import os
import requests
import secrets
import time
from datetime import datetime, timedelta
from flask import url_for

# PesaPal API configuration
class PesaPalConfig:
    """Configuration for PesaPal API"""
    BASE_URL = "https://pay.pesapal.com/v3"  # Use this for production
    # BASE_URL = "https://cybqa.pesapal.com/pesapalv3"  # Use this for sandbox testing
    
    def __init__(self):
        self.consumer_key = os.environ.get('PESAPAL_CONSUMER_KEY')
        self.consumer_secret = os.environ.get('PESAPAL_CONSUMER_SECRET')
        self.access_token = None
        self.token_expiry = None
    
    def get_access_token(self):
        """Get access token from PesaPal API"""
        # Check if we have a valid token
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
            
        # Get new token
        url = f"{self.BASE_URL}/api/Auth/RequestToken"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get('token')
            # Set token expiry to 55 minutes from now (60 min is the actual expiry)
            self.token_expiry = datetime.now() + timedelta(minutes=55)
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.text}")


class PesaPalPayment:
    """Handle payments via PesaPal"""
    
    def __init__(self):
        self.config = PesaPalConfig()
    
    def register_ipn_url(self, ipn_url):
        """Register IPN URL with PesaPal"""
        url = f"{self.config.BASE_URL}/api/URLSetup/RegisterIPN"
        token = self.config.get_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        payload = {
            "url": ipn_url,
            "ipn_notification_type": "GET"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        return response.json()
    
    def submit_order(self, user, amount, description, payment_type="subscription", redirect_url=None):
        """Submit order to PesaPal and get payment URL"""
        url = f"{self.config.BASE_URL}/api/Transactions/SubmitOrderRequest"
        token = self.config.get_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        # Generate a unique transaction ID
        transaction_id = f"TRX-{int(time.time())}-{secrets.token_hex(4)}"
        
        payload = {
            "id": transaction_id,
            "currency": "KES",
            "amount": amount,
            "description": description,
            "callback_url": redirect_url,
            "notification_id": "ipn-Kenya-Legal-System",
            "billing_address": {
                "email_address": user.email,
                "phone_number": "",  # Add phone field to user model
                "country_code": "KE",
                "first_name": user.first_name or user.username,
                "last_name": user.last_name or "",
                "line_1": "",
                "line_2": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "zip_code": ""
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            
            # Save the payment record in the database
            from app import db
            from models import Payment
            
            payment = Payment(
                amount=amount,
                payment_type=payment_type,
                payment_method='pesapal',
                transaction_id=transaction_id,
                status='pending',
                payment_data=json.dumps(data),
                user_id=user.id
            )
            
            if payment_type == 'subscription' and hasattr(user, 'selected_subscription_id'):
                payment.subscription_id = user.selected_subscription_id
                
            if payment_type == 'tokens' and hasattr(user, 'selected_token_package_id'):
                payment.token_package_id = user.selected_token_package_id
                
            db.session.add(payment)
            db.session.commit()
            
            return data.get('redirect_url'), payment
        else:
            raise Exception(f"Failed to submit order: {response.text}")
    
    def get_transaction_status(self, order_tracking_id):
        """Get transaction status from PesaPal"""
        url = f"{self.config.BASE_URL}/api/Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}"
        token = self.config.get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get transaction status: {response.text}")
    
    def process_ipn_notification(self, order_tracking_id, order_notification_type):
        """Process IPN notification from PesaPal"""
        # Get transaction status
        status_data = self.get_transaction_status(order_tracking_id)
        
        # Update payment record in database
        from app import db
        from models import Payment, User, Subscription, TokenPackage
        
        # Find payment by order_tracking_id in the payment_data JSON
        payment = Payment.query.filter(
            Payment.payment_data.like(f'%{order_tracking_id}%')
        ).first()
        
        if not payment:
            return False, "Payment not found"
            
        # Update payment status
        payment_status = status_data.get('payment_status_info', {}).get('payment_status')
        if payment_status == "COMPLETED":
            payment.status = 'completed'
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
        
        elif payment_status == "FAILED":
            payment.status = 'failed'
            db.session.commit()
            return False, "Payment failed"
        
        else:
            # Payment still pending
            return False, f"Payment in status: {payment_status}"