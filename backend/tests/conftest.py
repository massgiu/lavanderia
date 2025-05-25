import pytest
import tempfile
import os
from werkzeug.security import generate_password_hash

# Adjust the path to import app and db from the parent directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app, db as sqlalchemy_db, User

@pytest.fixture(scope='function') # Changed from 'session' to 'function' for DB isolation
def app():
    """Function-scoped test `Flask` application."""
    
    db_fd, db_path = tempfile.mkstemp(suffix='.sqlite')
    
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SECRET_KEY": "test_secret_key",
        "WTF_CSRF_ENABLED": False, 
        "LOGIN_DISABLED": False 
    })

    with flask_app.app_context():
        # Explicitly close session and dispose engine to ensure new DB URI is used
        sqlalchemy_db.session.remove()
        if sqlalchemy_db.engine: # Check if engine exists before disposing
            sqlalchemy_db.engine.dispose()
        
        sqlalchemy_db.create_all()

    yield flask_app

    # Teardown DB
    with flask_app.app_context(): # Ensure app context for teardown operations
        sqlalchemy_db.session.remove()
        sqlalchemy_db.drop_all()
        if sqlalchemy_db.engine: # Check if engine exists before disposing
            sqlalchemy_db.engine.dispose()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function') # Ensure client is also function-scoped if app is
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture()
def db(app):
    """Session-wide test database."""
    # This fixture provides the db object. DB setup/teardown is handled by the 'app' fixture.
    return sqlalchemy_db


@pytest.fixture
def new_user_data():
    return {
        'name': 'Test',
        'surname': 'User',
        'email': 'test@example.com',
        'password': 'password123',
        'phone_number': '1234567890',
        'address': '123 Test St',
        'city': 'Testville',
        'state': 'TS',
        'postal_code': '12345'
    }

@pytest.fixture
def registered_user(client, new_user_data, db):
    # Register a new user
    client.post('/api/register', json={
        'name': new_user_data['name'],
        'surname': new_user_data['surname'],
        'email': new_user_data['email'],
        'password': new_user_data['password']
    })
    # The user is registered, but not logged in by this fixture.
    # Fetch the user from DB to return the User object for further use if needed
    user = User.query.filter_by(email=new_user_data['email']).first()
    return user # This user object can be used to log in or as a target for operations

@pytest.fixture
def logged_in_user(client, new_user_data, db): # Depends on new_user_data to ensure consistency
    # First, ensure the user is registered
    client.post('/api/register', json={
        'name': new_user_data['name'],
        'surname': new_user_data['surname'],
        'email': new_user_data['email'],
        'password': new_user_data['password']
    })
    # Then, log in
    response = client.post('/api/login', json={
        'email': new_user_data['email'],
        'password': new_user_data['password']
    })
    assert response.status_code == 200 # Ensure login was successful
    # Return the user object along with the client for making authenticated requests
    user = User.query.filter_by(email=new_user_data['email']).first()
    return {'client': client, 'user': user, 'user_data': response.get_json()['user']}

@pytest.fixture
def admin_user_data():
    return {
        'name': 'Admin',
        'surname': 'User',
        'email': 'admin@example.com',
        'password': 'adminpassword',
        'is_owner': True
    }

@pytest.fixture
def logged_in_admin(client, admin_user_data, db):
    # Create and register the admin user
    admin = User(
        name=admin_user_data['name'],
        surname=admin_user_data['surname'],
        email=admin_user_data['email'],
        password_hash=generate_password_hash(admin_user_data['password'], method='pbkdf2:sha256'),
        is_owner=admin_user_data['is_owner']
    )
    db.session.add(admin)
    db.session.commit()

    # Log in the admin user
    response = client.post('/api/login', json={
        'email': admin_user_data['email'],
        'password': admin_user_data['password']
    })
    assert response.status_code == 200
    # Return the admin user object along with the client
    # The user object from db might be more up-to-date if login response is minimal
    admin_db_user = User.query.filter_by(email=admin_user_data['email']).first()
    return {'client': client, 'user': admin_db_user, 'user_data': response.get_json()['user']}
