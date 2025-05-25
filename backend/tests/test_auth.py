import pytest
import json
import os

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import User # Assuming User model is directly accessible from app for query

# Test Registration
def test_register_user_success(client, new_user_data, db):
    response = client.post('/api/register', json=new_user_data)
    assert response.status_code == 201
    assert response.json['message'] == 'User registered successfully'
    
    # Verify user in database
    user = User.query.filter_by(email=new_user_data['email']).first()
    assert user is not None
    assert user.name == new_user_data['name']

def test_register_user_existing_email(client, new_user_data, db):
    # First registration
    client.post('/api/register', json=new_user_data)
    
    # Attempt to register again with the same email
    response = client.post('/api/register', json=new_user_data)
    assert response.status_code == 409
    assert response.json['message'] == 'Email already exists'

def test_register_user_missing_email(client, new_user_data):
    data = new_user_data.copy()
    del data['email']
    response = client.post('/api/register', json=data)
    assert response.status_code == 400
    assert response.json['message'] == 'Email and password are required'

def test_register_user_missing_password(client, new_user_data):
    data = new_user_data.copy()
    del data['password']
    response = client.post('/api/register', json=data)
    assert response.status_code == 400
    assert response.json['message'] == 'Email and password are required'

# Test Login
def test_login_user_success(client, registered_user, new_user_data): # Uses registered_user to ensure user exists
    login_data = {
        'email': new_user_data['email'],
        'password': new_user_data['password']
    }
    response = client.post('/api/login', json=login_data)
    assert response.status_code == 200
    assert response.json['message'] == 'Login successful'
    assert response.json['user']['email'] == new_user_data['email']
    assert 'password_hash' not in response.json['user'] # Ensure password hash isn't returned

def test_login_user_incorrect_password(client, registered_user, new_user_data):
    login_data = {
        'email': new_user_data['email'],
        'password': 'wrongpassword'
    }
    response = client.post('/api/login', json=login_data)
    assert response.status_code == 401
    assert response.json['message'] == 'Invalid email or password'

def test_login_user_non_existent_email(client, new_user_data):
    login_data = {
        'email': 'nonexistent@example.com',
        'password': new_user_data['password']
    }
    response = client.post('/api/login', json=login_data)
    assert response.status_code == 401
    assert response.json['message'] == 'Invalid email or password'

def test_login_user_missing_email(client):
    response = client.post('/api/login', json={'password': 'somepassword'})
    assert response.status_code == 400
    assert response.json['message'] == 'Email and password are required'

def test_login_user_missing_password(client):
    response = client.post('/api/login', json={'email': 'test@example.com'})
    assert response.status_code == 400
    assert response.json['message'] == 'Email and password are required'


# Test Logout
def test_logout_user_success(logged_in_user): # uses logged_in_user fixture
    client = logged_in_user['client']
    response = client.post('/api/logout')
    assert response.status_code == 200
    assert response.json['message'] == 'Logout successful'

    # Try accessing a protected route or checking current_user after logout
    # For example, if there was an /api/me endpoint:
    # me_response = client.get('/api/me') # Assuming /api/me requires login
    # assert me_response.status_code == 401 # Should be unauthorized

def test_logout_user_not_logged_in(client):
    response = client.post('/api/logout')
    # Flask-Login typically redirects to login_view or returns 401 if login_view is not set
    # For an API, it should ideally be 401.
    # The default behavior if login_manager.unauthorized() is not customized might vary.
    # Let's assume it correctly returns 401 as per Flask-Login's default for XHR.
    assert response.status_code == 401 # Or check for redirect if login_view is configured
                                       # Default Flask-Login behavior for @login_required is 401
                                       # if request.is_xhr or prefers JSON.
                                       # Test client requests might not always be treated as XHR by default.
                                       # If this fails due to redirect, conftest.py's client
                                       # or app config may need adjustment, or the endpoint behavior for unauthorized access.
                                       # For now, assuming 401 is the expected API behavior.
    # If the login_manager's unauthorized handler returns HTML, the content type will be different.
    # assert response.json['message'] == 'Unauthorized' # Or similar, depending on error response format.
    # For Flask-Login, the default 401 response does not include a JSON body.
    # So, we might only check the status code.
    # For an API, it's good practice to have the unauthorized handler return JSON.
    # Flask-Login's default behavior for AJAX requests (which test_client might simulate) is a 401.
    # If it's redirecting, that means it's not being treated as an AJAX request.
    # The `app.config['LOGIN_DISABLED'] = False` in conftest.py is important.

    # Let's check the specific behavior of the app's unauthorized handler or Flask-Login's default.
    # Given the setup, a 401 is expected.
    # If Flask-Login is configured with a login_view, it might redirect to that view (e.g., 302 Found).
    # However, for an API, we'd expect a 401. Let's assume that's the case.
    # The test client in Flask does not automatically send X-Requested-With header.
    # Flask-Login checks for this header to return 401 for AJAX, otherwise redirects.
    # To force 401, we can add the header:
    # response = client.post('/api/logout', headers={'X-Requested-With': 'XMLHttpRequest'})
    # assert response.status_code == 401
    # For now, we'll stick to the current test and see. It's likely to be 401 with Flask-Login's setup
    # when @login_required is used.

    # The /api/logout endpoint is decorated with @login_required.
    # If not logged in, Flask-Login's default unauthorized() will be called.
    # This usually means a 401 response.
    # If a login_manager.login_view is set, it might redirect.
    # Our app.py does not set a login_view, so 401 is expected.
    # The default response for 401 from Flask-Login is just a plain 401, no JSON.
    # So we only assert the status code.
    assert response.status_code == 401
