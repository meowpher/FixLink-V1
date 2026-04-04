def test_admin_dashboard_access(client, admin_user, student_user, professional_user):
    """Test that only admins can access the admin dashboard."""
    
    # 1. Unauthenticated request
    response = client.get('/admin/')
    assert response.status_code == 302 # Redirects to login
    
    # 2. Student request
    with client.session_transaction() as sess:
        sess['user_id'] = student_user.id
        sess['is_admin'] = False
    
    response = client.get('/admin/')
    assert response.status_code == 403 # Forbidden
    
    # 3. Professional request
    with client.session_transaction() as sess:
        sess.clear()
        sess['professional_id'] = professional_user.id
    
    response = client.get('/admin/')
    assert response.status_code == 302 # Redirects to main login (not recognized as user)
    
    # 4. Admin request
    with client.session_transaction() as sess:
        sess.clear()
        sess['user_id'] = admin_user.id
        sess['is_admin'] = True
        
    response = client.get('/admin/')
    assert response.status_code == 200 # OK
