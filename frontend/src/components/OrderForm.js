import React, { useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '/api';

const OrderForm = ({ cart, total, onOrderComplete }) => {
  const [customerData, setCustomerData] = useState({
    name: '',
    email: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [orderStatus, setOrderStatus] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setCustomerData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear validation error for this field when user types
    if (validationErrors[name]) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: null
      }));
    }
  };

  const validateForm = () => {
    const errors = {};

    // Validate name - only letters, spaces, hyphens, apostrophes
    if (!customerData.name.trim()) {
      errors.name = 'Name is required';
    } else if (!/^[a-zA-Z\s\-']+$/.test(customerData.name)) {
      errors.name = 'Name can only contain letters, spaces, hyphens, and apostrophes';
    }

    // Validate email - stricter than HTML5
    if (!customerData.email.trim()) {
      errors.email = 'Email is required';
    } else {
      // More strict email validation requiring TLD
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(customerData.email)) {
        errors.email = 'Please enter a valid email address (e.g., user@example.com)';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setOrderStatus(null);

    // Validate form before submitting
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const orderData = {
        customer_name: customerData.name,
        customer_email: customerData.email,
        items: cart.map(item => ({
          id: item.id,
          name: item.name,
          price: item.price,
          quantity: item.quantity
        }))
      };

      const response = await axios.post(`${API_URL}/orders`, orderData);

      setOrderStatus({
        type: 'success',
        message: `Order #${response.data.id} placed successfully! Thank you for your order.`
      });

      // Clear the form and cart
      setCustomerData({ name: '', email: '' });
      setTimeout(() => {
        onOrderComplete();
        setOrderStatus(null);
      }, 3000);

    } catch (error) {
      console.error('Order submission error:', error);
      console.log('Error response data:', error.response?.data);

      let errorMessage = 'Failed to place order. Please try again.';
      let errorDetails = null;

      if (error.response) {
        // Server responded with an error status
        const status = error.response.status;
        const data = error.response.data;
        console.log('Status:', status, 'Data:', data);

        if (status === 422) {
          // Validation error
          errorMessage = 'Please check your order details:';
          console.log('422 error - checking for errors array:', data.errors);
          console.log('422 error - checking for detail:', data.detail);

          if (data.errors && Array.isArray(data.errors) && data.errors.length > 0) {
            // Custom error format from backend validation_exception_handler
            console.log('Using custom errors format');
            errorDetails = data.errors.map(err => {
              const field = err.field || 'unknown';
              const message = err.message || err.msg || 'Invalid value';
              return `${field}: ${message}`;
            });
            console.log('Parsed error details:', errorDetails);
          } else if (data.detail) {
            console.log('Checking detail field, type:', typeof data.detail);
            // Standard FastAPI validation error format
            if (Array.isArray(data.detail)) {
              console.log('Detail is array, parsing...');
              errorDetails = data.detail.map(err => {
                // Format: { loc: ["body", "field"], msg: "error message", type: "error_type" }
                const field = err.loc && err.loc.length > 1 ? err.loc[err.loc.length - 1] : 'field';
                const message = err.msg || err.message || 'Invalid value';
                return `${field}: ${message}`;
              });
            } else if (typeof data.detail === 'string' && data.detail !== 'Validation error') {
              // Single error message (but not the generic "Validation error")
              errorDetails = [data.detail];
            }
          }

          console.log('Final errorDetails:', errorDetails);

          // If no specific errors were found, show generic message
          if (!errorDetails || errorDetails.length === 0) {
            console.log('No error details found, using fallback');
            errorDetails = ['Invalid data provided. Please check your inputs.'];
          }
        } else if (status === 500) {
          errorMessage = 'Server error. Please try again later.';
          if (data.detail) {
            errorDetails = [data.detail];
          }
        } else if (status === 400) {
          errorMessage = data.detail || 'Invalid request. Please check your input.';
        } else {
          errorMessage = data.detail || `Error: ${status}`;
        }
      } else if (error.request) {
        // Request was made but no response received
        errorMessage = 'Cannot connect to server. Please check your connection.';
      }

      const statusToSet = {
        type: 'error',
        message: errorMessage,
        details: errorDetails
      };
      console.log('Setting orderStatus to:', statusToSet);
      setOrderStatus(statusToSet);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Debug logging
  if (orderStatus && orderStatus.type === 'error') {
    console.log('Rendering error status:', orderStatus);
    console.log('Has details?', !!orderStatus.details);
    console.log('Details length:', orderStatus.details?.length);
  }

  return (
    <div className="order-form">
      <h3>Complete Your Order</h3>

      {orderStatus && (
        <div style={{
          padding: '1rem',
          borderRadius: '4px',
          marginBottom: '1rem',
          backgroundColor: orderStatus.type === 'success' ? '#d4edda' : '#f8d7da',
          color: orderStatus.type === 'success' ? '#155724' : '#721c24',
          border: `1px solid ${orderStatus.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: orderStatus.details ? '0.5rem' : '0' }}>
            {orderStatus.message}
          </div>
          {orderStatus.details && orderStatus.details.length > 0 && (
            <ul style={{
              margin: '0.5rem 0 0 0',
              paddingLeft: '1.5rem',
              fontSize: '0.9rem'
            }}>
              {orderStatus.details.map((detail, index) => (
                <li key={index} style={{ marginBottom: '0.25rem' }}>
                  {detail}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="name">Full Name</label>
          <input
            type="text"
            id="name"
            name="name"
            value={customerData.name}
            onChange={handleInputChange}
            disabled={isSubmitting}
            style={{
              borderColor: validationErrors.name ? '#dc3545' : undefined
            }}
          />
          {validationErrors.name && (
            <div style={{
              color: '#dc3545',
              fontSize: '0.875rem',
              marginTop: '0.25rem'
            }}>
              {validationErrors.name}
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="email">Email Address</label>
          <input
            type="email"
            id="email"
            name="email"
            value={customerData.email}
            onChange={handleInputChange}
            disabled={isSubmitting}
            style={{
              borderColor: validationErrors.email ? '#dc3545' : undefined
            }}
          />
          {validationErrors.email && (
            <div style={{
              color: '#dc3545',
              fontSize: '0.875rem',
              marginTop: '0.25rem'
            }}>
              {validationErrors.email}
            </div>
          )}
        </div>

        <div style={{ 
          background: '#f8f9fa', 
          padding: '1rem', 
          borderRadius: '4px',
          marginBottom: '1rem'
        }}>
          <h4 style={{ margin: '0 0 0.5rem 0' }}>Order Summary</h4>
          {cart.map(item => (
            <div key={item.id} style={{ 
              display: 'flex', 
              justifyContent: 'space-between',
              marginBottom: '0.25rem'
            }}>
              <span>{item.name} x {item.quantity}</span>
              <span>${(item.price * item.quantity).toFixed(2)}</span>
            </div>
          ))}
          <div style={{ 
            borderTop: '1px solid #dee2e6',
            paddingTop: '0.5rem',
            marginTop: '0.5rem',
            fontWeight: 'bold'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Total:</span>
              <span>${total.toFixed(2)}</span>
            </div>
          </div>
        </div>

        <button 
          type="submit" 
          className="btn" 
          disabled={isSubmitting || cart.length === 0}
          style={{ 
            width: '100%',
            padding: '1rem',
            fontSize: '1.1rem'
          }}
        >
          {isSubmitting ? 'Placing Order...' : `Place Order - $${total.toFixed(2)}`}
        </button>
      </form>
    </div>
  );
};

export default OrderForm;