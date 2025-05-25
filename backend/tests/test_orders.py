import pytest
import json
from app import Order, User # Assuming Order model is accessible

# Helper to create an order directly for setup purposes if needed
def create_order_directly(db, user_id, items_description="Test items", total_price=10.0):
    order = Order(user_id=user_id, items_description=items_description, total_price=total_price)
    db.session.add(order)
    db.session.commit()
    return order

# Test Order Creation (/api/orders - POST)
def test_create_order_success(logged_in_user):
    client = logged_in_user['client']
    user = logged_in_user['user']
    
    order_data = {
        'items_description': '2 shirts, 1 pant',
        'pickup_date': '2024-08-01T10:00:00',
        'delivery_date': '2024-08-03T10:00:00',
        'total_price': 25.50
    }
    response = client.post('/api/orders', json=order_data)
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['user_id'] == user.id
    assert data['items_description'] == order_data['items_description']
    assert data['total_price'] == order_data['total_price']
    assert Order.query.count() == 1

def test_create_order_missing_items_description(logged_in_user):
    client = logged_in_user['client']
    order_data = { # Missing items_description
        'total_price': 25.50
    }
    response = client.post('/api/orders', json=order_data)
    assert response.status_code == 400
    assert response.get_json()['message'] == 'Items description is required'

def test_create_order_not_logged_in(client):
    order_data = {'items_description': 'Test items', 'total_price': 10.0}
    response = client.post('/api/orders', json=order_data)
    assert response.status_code == 401 # Expecting 401 Unauthorized


# Test Get User's Orders (/api/orders - GET)
def test_get_user_orders_success(logged_in_user, db):
    client = logged_in_user['client']
    user = logged_in_user['user']
    
    # Create some orders for this user directly
    create_order_directly(db, user.id, "Order 1 items", 15.0)
    create_order_directly(db, user.id, "Order 2 items", 20.0)
    
    # Create an order for another user to ensure filtering
    other_user = User(name="Other", surname="User", email="other@example.com", password_hash="abc")
    db.session.add(other_user)
    db.session.commit()
    create_order_directly(db, other_user.id, "Other user order", 50.0)

    response = client.get('/api/orders')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2 # Should only get orders for the logged_in_user
    assert data[0]['items_description'] == "Order 1 items"
    assert data[1]['items_description'] == "Order 2 items"

def test_get_user_orders_no_orders(logged_in_user):
    client = logged_in_user['client']
    response = client.get('/api/orders')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_get_user_orders_not_logged_in(client):
    response = client.get('/api/orders')
    assert response.status_code == 401


# Test Admin - Get All Orders (/api/admin/orders - GET)
def test_admin_get_all_orders_success(logged_in_admin, db, registered_user): # registered_user fixture to create a normal user
    admin_client = logged_in_admin['client']
    
    # Create an order for the normal user
    create_order_directly(db, registered_user.id, "Normal user order", 30.0)
    # Create an order for the admin themselves (or another user)
    create_order_directly(db, logged_in_admin['user'].id, "Admin's own order", 40.0)
    
    response = admin_client.get('/api/admin/orders')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2 # Should see both orders
    # Check if user details are included (as per include_user=True in endpoint)
    assert 'user' in data[0] 
    assert data[0]['user']['email'] == registered_user.email or data[1]['user']['email'] == registered_user.email

def test_admin_get_all_orders_forbidden_for_normal_user(logged_in_user):
    client = logged_in_user['client']
    response = client.get('/api/admin/orders')
    assert response.status_code == 403 # Forbidden

def test_admin_get_all_orders_not_logged_in(client):
    response = client.get('/api/admin/orders')
    assert response.status_code == 401


# Test Admin - Update Order Status (/api/admin/orders/<order_id>/status - PUT)
def test_admin_update_order_status_success(logged_in_admin, db, registered_user):
    admin_client = logged_in_admin['client']
    # Create an order by the normal user
    order = create_order_directly(db, registered_user.id, "Order to update status", 22.0)
    assert order.status == 'Pending' # Initial status
    
    new_status = 'Processing'
    response = admin_client.put(f'/api/admin/orders/{order.id}/status', json={'status': new_status})
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == order.id
    assert data['status'] == new_status
    
    # Verify in DB
    updated_order = db.session.get(Order, order.id)
    assert updated_order.status == new_status

def test_admin_update_order_status_non_admin(logged_in_user, db):
    client = logged_in_user['client']
    # Create an order (user doesn't matter here as access is denied before DB interaction)
    order = create_order_directly(db, logged_in_user['user'].id, "Test order", 10)
    
    response = client.put(f'/api/admin/orders/{order.id}/status', json={'status': 'Processing'})
    assert response.status_code == 403

def test_admin_update_order_status_not_logged_in(client, db, registered_user):
    order = create_order_directly(db, registered_user.id, "Test order", 10)
    response = client.put(f'/api/admin/orders/{order.id}/status', json={'status': 'Processing'})
    assert response.status_code == 401

def test_admin_update_order_status_non_existent_order(logged_in_admin):
    admin_client = logged_in_admin['client']
    non_existent_order_id = 99999
    response = admin_client.put(f'/api/admin/orders/{non_existent_order_id}/status', json={'status': 'Processing'})
    assert response.status_code == 404
    assert response.get_json()['message'] == 'Order not found'

def test_admin_update_order_status_invalid_status_value(logged_in_admin, db, registered_user):
    admin_client = logged_in_admin['client']
    order = create_order_directly(db, registered_user.id, "Order for invalid status test", 25.0)
    
    invalid_status = 'ShippedOutOfExistence'
    response = admin_client.put(f'/api/admin/orders/{order.id}/status', json={'status': invalid_status})
    assert response.status_code == 400
    assert 'Invalid status' in response.get_json()['message']

def test_admin_update_order_status_missing_status_value(logged_in_admin, db, registered_user):
    admin_client = logged_in_admin['client']
    order = create_order_directly(db, registered_user.id, "Order for missing status test", 25.0)
    
    response = admin_client.put(f'/api/admin/orders/{order.id}/status', json={}) # Missing status
    assert response.status_code == 400
    assert response.get_json()['message'] == 'Status is required'
