import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '/api';

const OrderHistory = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log('OrderHistory component mounted, fetching orders...');
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      console.log('fetchOrders called, setting loading to true');
      setLoading(true);
      const response = await axios.get(`${API_URL}/orders`);
      console.log('Orders fetched successfully:', response.data);
      setOrders(response.data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
      setError(null);
    } catch (err) {
      console.error('Error fetching orders:', err);

      let errorMessage = 'Failed to load orders. Please try again.';

      if (err.response) {
        const status = err.response.status;
        const data = err.response.data;

        if (status === 500) {
          errorMessage = 'Server error while loading orders.';
        } else if (status === 404) {
          errorMessage = 'Orders endpoint not found.';
        } else if (data.detail) {
          errorMessage = data.detail;
        }
      } else if (err.request) {
        errorMessage = 'Cannot connect to server. Please check your connection.';
      }

      setError(errorMessage);
    } finally {
      console.log('Setting loading to false');
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const parseOrderItems = (itemsString) => {
    try {
      return JSON.parse(itemsString);
    } catch {
      return [];
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <h2>Loading orders...</h2>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error">
        <h2>Error</h2>
        <p>{error}</p>
        <button className="btn" onClick={fetchOrders}>
          Try Again
        </button>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="no-orders">
        <h2>Order History</h2>
        <p>No orders found. Place your first order to see it here!</p>
      </div>
    );
  }

  return (
    <div className="order-history">
      <h2>Order History</h2>
      <p>Total orders: {orders.length}</p>
      
      <div className="orders-list">
        {orders.map((order) => {
          const orderItems = parseOrderItems(order.items);
          return (
            <div key={order.id} className="order-card">
              <div className="order-header">
                <div className="order-info">
                  <h3>Order #{order.id}</h3>
                  <p className="order-date">{formatDate(order.created_at)}</p>
                </div>
                <div className="order-total">
                  <span className="total-amount">${order.total_amount.toFixed(2)}</span>
                  <span className={`status status-${order.status}`}>{order.status}</span>
                </div>
              </div>
              
              <div className="customer-info">
                <p><strong>Customer:</strong> {order.customer_name}</p>
                <p><strong>Email:</strong> {order.customer_email}</p>
              </div>
              
              <div className="order-items">
                <h4>Items:</h4>
                <ul>
                  {orderItems.map((item, index) => (
                    <li key={index} className="order-item">
                      <span className="item-name">{item.name}</span>
                      <span className="item-details">
                        Qty: {item.quantity} × ${item.price.toFixed(2)} = ${(item.quantity * item.price).toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default OrderHistory;