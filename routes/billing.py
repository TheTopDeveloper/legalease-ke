from datetime import datetime
import json

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc

from app import db
from models import User, Subscription, TokenPackage, Payment, TokenUsage
from utils.pesapal import PesaPalPayment

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/subscriptions')
@login_required
def subscriptions():
    """View available subscription plans"""
    # Get all active subscription plans
    individual_plans = Subscription.query.filter_by(is_active=True, is_organization=False).all()
    organization_plans = Subscription.query.filter_by(is_active=True, is_organization=True).all()
    
    # Get user's current subscription
    current_plan = None
    if current_user.account_type != 'free':
        current_plan = Subscription.query.filter_by(name=current_user.account_type).first()
    
    return render_template(
        'billing/subscriptions.html',
        individual_plans=individual_plans,
        organization_plans=organization_plans,
        current_plan=current_plan
    )

@billing_bp.route('/tokens')
@login_required
def tokens():
    """View available token packages"""
    # Get all active token packages
    token_packages = TokenPackage.query.filter_by(is_active=True).all()
    
    # Get user's token usage history
    token_usage = TokenUsage.query.filter_by(user_id=current_user.id).order_by(desc(TokenUsage.created_at)).limit(10).all()
    
    return render_template(
        'billing/tokens.html',
        token_packages=token_packages,
        token_usage=token_usage,
        tokens_available=current_user.tokens_available
    )

@billing_bp.route('/subscribe/<int:subscription_id>', methods=['POST'])
@login_required
def subscribe(subscription_id):
    """Subscribe to a plan"""
    # Get the subscription
    subscription = Subscription.query.get_or_404(subscription_id)
    
    if not subscription.is_active:
        flash('This subscription plan is not currently available.', 'danger')
        return redirect(url_for('billing.subscriptions'))
    
    # Check if it's an organization plan and user role is appropriate
    if subscription.is_organization and current_user.role != 'organization':
        flash('You need an organization account for this subscription.', 'danger')
        return redirect(url_for('billing.subscriptions'))
    
    # Store selected subscription in session for later
    current_user.selected_subscription_id = subscription.id
    db.session.commit()
    
    # Initialize PesaPal payment
    pesapal = PesaPalPayment()
    
    try:
        # Prepare the callback URL for after payment
        callback_url = url_for('billing.payment_callback', _external=True)
        
        # Submit order to PesaPal
        payment_url, payment = pesapal.submit_order(
            user=current_user,
            amount=subscription.price,
            description=f"{subscription.name.capitalize()} subscription - {subscription.duration_days} days",
            payment_type="subscription",
            redirect_url=callback_url
        )
        
        # Store payment ID in session
        session['payment_id'] = payment.id
        
        # Redirect to PesaPal payment page
        return redirect(payment_url)
        
    except Exception as e:
        flash(f'Payment error: {str(e)}', 'danger')
        return redirect(url_for('billing.subscriptions'))

@billing_bp.route('/buy-tokens/<int:package_id>', methods=['POST'])
@login_required
def buy_tokens(package_id):
    """Buy a token package"""
    # Get the token package
    token_package = TokenPackage.query.get_or_404(package_id)
    
    if not token_package.is_active:
        flash('This token package is not currently available.', 'danger')
        return redirect(url_for('billing.tokens'))
    
    # Store selected token package in session for later
    current_user.selected_token_package_id = token_package.id
    db.session.commit()
    
    # Initialize PesaPal payment
    pesapal = PesaPalPayment()
    
    try:
        # Prepare the callback URL for after payment
        callback_url = url_for('billing.payment_callback', _external=True)
        
        # Submit order to PesaPal
        payment_url, payment = pesapal.submit_order(
            user=current_user,
            amount=token_package.price,
            description=f"{token_package.name} Token Package - {token_package.token_count} tokens",
            payment_type="tokens",
            redirect_url=callback_url
        )
        
        # Store payment ID in session
        session['payment_id'] = payment.id
        
        # Redirect to PesaPal payment page
        return redirect(payment_url)
        
    except Exception as e:
        flash(f'Payment error: {str(e)}', 'danger')
        return redirect(url_for('billing.tokens'))

@billing_bp.route('/payment/callback')
def payment_callback():
    """Handle payment callback from PesaPal"""
    # Get parameters from callback
    order_tracking_id = request.args.get('OrderTrackingId')
    order_merchant_reference = request.args.get('OrderMerchantReference')
    order_notification_type = request.args.get('OrderNotificationType')
    
    if order_tracking_id:
        # Process the payment notification
        pesapal = PesaPalPayment()
        try:
            success, message = pesapal.process_ipn_notification(order_tracking_id, order_notification_type)
            
            if success:
                flash('Payment completed successfully!', 'success')
                # Clear payment ID from session
                if 'payment_id' in session:
                    session.pop('payment_id')
                    
                # Redirect based on payment type
                payment_id = session.get('payment_id')
                if payment_id:
                    payment = Payment.query.get(payment_id)
                    if payment:
                        if payment.payment_type == 'subscription':
                            return redirect(url_for('billing.subscriptions'))
                        elif payment.payment_type == 'tokens':
                            return redirect(url_for('billing.tokens'))
                
                # Default redirect
                return redirect(url_for('dashboard.index'))
                
            else:
                flash(f'Payment processing issue: {message}', 'warning')
                return redirect(url_for('billing.payment_status'))
                
        except Exception as e:
            flash(f'Error processing payment: {str(e)}', 'danger')
            return redirect(url_for('billing.payment_status'))
    
    # If no tracking ID, redirect to payment status page
    flash('No payment information received.', 'warning')
    return redirect(url_for('billing.payment_status'))

@billing_bp.route('/payment/status')
@login_required
def payment_status():
    """Check payment status"""
    payment_id = session.get('payment_id')
    
    if not payment_id:
        flash('No active payment found.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    payment = Payment.query.get(payment_id)
    
    if not payment:
        flash('Payment not found.', 'danger')
        if 'payment_id' in session:
            session.pop('payment_id')
        return redirect(url_for('dashboard.index'))
    
    # If payment is pending, check status with PesaPal
    if payment.status == 'pending':
        try:
            # Get payment data
            payment_data = json.loads(payment.payment_data)
            order_tracking_id = payment_data.get('order_tracking_id')
            
            if order_tracking_id:
                pesapal = PesaPalPayment()
                status_data = pesapal.get_transaction_status(order_tracking_id)
                
                # Process status data
                payment_status = status_data.get('payment_status_info', {}).get('payment_status')
                
                if payment_status == "COMPLETED":
                    # Process successful payment
                    success, message = pesapal.process_ipn_notification(order_tracking_id, "CONFIRMATION")
                    if success:
                        flash('Payment completed successfully!', 'success')
                        # Clear payment ID from session
                        if 'payment_id' in session:
                            session.pop('payment_id')
                        
                        if payment.payment_type == 'subscription':
                            return redirect(url_for('billing.subscriptions'))
                        else:
                            return redirect(url_for('billing.tokens'))
                
                elif payment_status == "FAILED":
                    payment.status = 'failed'
                    db.session.commit()
                    flash('Payment failed.', 'danger')
                    
        except Exception as e:
            flash(f'Error checking payment status: {str(e)}', 'danger')
    
    return render_template('billing/payment_status.html', payment=payment)

@billing_bp.route('/billing/history')
@login_required
def payment_history():
    """View payment history"""
    payments = Payment.query.filter_by(user_id=current_user.id).order_by(desc(Payment.created_at)).all()
    
    return render_template('billing/history.html', payments=payments)

@billing_bp.route('/ipn/notification', methods=['GET', 'POST'])
def ipn_notification():
    """Handle IPN notifications from PesaPal"""
    # This endpoint will be called by PesaPal when payment status changes
    
    # Get parameters from request
    order_tracking_id = request.args.get('OrderTrackingId')
    order_merchant_reference = request.args.get('OrderMerchantReference')
    order_notification_type = request.args.get('OrderNotificationType')
    
    if order_tracking_id:
        # Process the payment notification
        pesapal = PesaPalPayment()
        try:
            success, message = pesapal.process_ipn_notification(order_tracking_id, order_notification_type)
            return jsonify({'success': success, 'message': message})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'No OrderTrackingId provided'}), 400


# Admin routes for managing subscriptions and token packages

@billing_bp.route('/admin/subscriptions')
@login_required
def admin_subscriptions():
    """Admin view for managing subscription plans"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    subscriptions = Subscription.query.all()
    return render_template('admin/subscriptions.html', subscriptions=subscriptions)

@billing_bp.route('/admin/subscriptions/create', methods=['GET', 'POST'])
@login_required
def create_subscription():
    """Create a new subscription plan"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Create a new subscription plan
        subscription = Subscription(
            name=request.form.get('name'),
            price=float(request.form.get('price')),
            duration_days=int(request.form.get('duration_days')),
            max_cases=int(request.form.get('max_cases')),
            tokens_included=int(request.form.get('tokens_included')),
            is_organization=bool(request.form.get('is_organization')),
            max_users=int(request.form.get('max_users', 1)),
            is_active=bool(request.form.get('is_active')),
            features=request.form.get('features')
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        flash('Subscription plan created successfully.', 'success')
        return redirect(url_for('billing.admin_subscriptions'))
    
    return render_template('admin/create_subscription.html')

@billing_bp.route('/admin/subscriptions/edit/<int:subscription_id>', methods=['GET', 'POST'])
@login_required
def edit_subscription(subscription_id):
    """Edit a subscription plan"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    subscription = Subscription.query.get_or_404(subscription_id)
    
    if request.method == 'POST':
        # Update subscription plan
        subscription.name = request.form.get('name')
        subscription.price = float(request.form.get('price'))
        subscription.duration_days = int(request.form.get('duration_days'))
        subscription.max_cases = int(request.form.get('max_cases'))
        subscription.tokens_included = int(request.form.get('tokens_included'))
        subscription.is_organization = bool(request.form.get('is_organization'))
        subscription.max_users = int(request.form.get('max_users', 1))
        subscription.is_active = bool(request.form.get('is_active'))
        subscription.features = request.form.get('features')
        
        db.session.commit()
        
        flash('Subscription plan updated successfully.', 'success')
        return redirect(url_for('billing.admin_subscriptions'))
    
    return render_template('admin/edit_subscription.html', subscription=subscription)

@billing_bp.route('/admin/tokens')
@login_required
def admin_tokens():
    """Admin view for managing token packages"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    token_packages = TokenPackage.query.all()
    return render_template('admin/token_packages.html', token_packages=token_packages)

@billing_bp.route('/admin/tokens/create', methods=['GET', 'POST'])
@login_required
def create_token_package():
    """Create a new token package"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Create a new token package
        token_package = TokenPackage(
            name=request.form.get('name'),
            token_count=int(request.form.get('token_count')),
            price=float(request.form.get('price')),
            is_active=bool(request.form.get('is_active'))
        )
        
        db.session.add(token_package)
        db.session.commit()
        
        flash('Token package created successfully.', 'success')
        return redirect(url_for('billing.admin_tokens'))
    
    return render_template('admin/create_token_package.html')

@billing_bp.route('/admin/tokens/edit/<int:package_id>', methods=['GET', 'POST'])
@login_required
def edit_token_package(package_id):
    """Edit a token package"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    token_package = TokenPackage.query.get_or_404(package_id)
    
    if request.method == 'POST':
        # Update token package
        token_package.name = request.form.get('name')
        token_package.token_count = int(request.form.get('token_count'))
        token_package.price = float(request.form.get('price'))
        token_package.is_active = bool(request.form.get('is_active'))
        
        db.session.commit()
        
        flash('Token package updated successfully.', 'success')
        return redirect(url_for('billing.admin_tokens'))
    
    return render_template('admin/edit_token_package.html', token_package=token_package)

@billing_bp.route('/admin/give-tokens', methods=['GET', 'POST'])
@login_required
def give_tokens():
    """Admin function to give tokens to a user"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Get user and token count
        user_id = request.form.get('user_id')
        token_count = int(request.form.get('token_count'))
        
        user = User.query.get(user_id)
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('billing.give_tokens'))
        
        # Add tokens to user
        user.tokens_available += token_count
        
        # Create a payment record for tracking
        payment = Payment(
            amount=0,  # Free tokens
            payment_type='tokens',
            payment_method='manual',
            transaction_id=f"ADMIN-TOKENS-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status='completed',
            payment_data=json.dumps({
                'admin_user_id': current_user.id,
                'token_count': token_count,
                'reason': request.form.get('reason', 'Admin allocation')
            }),
            user_id=user.id,
            completed_at=datetime.now()
        )
        
        db.session.add(payment)
        db.session.commit()
        
        flash(f'Successfully added {token_count} tokens to {user.username}.', 'success')
        return redirect(url_for('billing.give_tokens'))
    
    # Get all users for the form
    users = User.query.all()
    
    return render_template('admin/give_tokens.html', users=users)