import React from 'react';

const Cart = ({ cart, onRemoveFromCart, onUpdateQuantity, total }) => {
  if (cart.length === 0) {
    return (
      <div className="cart-empty" style={{ 
        textAlign: 'center', 
        padding: '2rem',
        background: 'white',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <h3>Your cart is empty</h3>
        <p>Add some delicious kabobs to get started!</p>
      </div>
    );
  }

  return (
    <div className="cart-summary" style={{
      background: 'white',
      padding: '2rem',
      borderRadius: '8px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
    }}>
      <h3>Order Summary</h3>
      {cart.map(item => (
        <div key={item.id} className="cart-item" style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1rem 0',
          borderBottom: '1px solid #eee'
        }}>
          <div style={{ flex: 1 }}>
            <h4 style={{ margin: '0 0 0.5rem 0' }}>{item.name}</h4>
            <p style={{ margin: 0, color: '#666' }}>${item.price.toFixed(2)} each</p>
          </div>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '1rem' 
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button 
                className="btn"
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                onClick={() => onUpdateQuantity(item.id, item.quantity - 1)}
              >
                -
              </button>
              <span style={{ minWidth: '2rem', textAlign: 'center' }}>
                {item.quantity}
              </span>
              <button 
                className="btn"
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
              >
                +
              </button>
            </div>
            <div style={{ minWidth: '4rem', textAlign: 'right', fontWeight: 'bold' }}>
              ${(item.price * item.quantity).toFixed(2)}
            </div>
            <button 
              onClick={() => onRemoveFromCart(item.id)}
              style={{
                background: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                padding: '0.25rem 0.5rem',
                cursor: 'pointer',
                fontSize: '0.8rem'
              }}
            >
              Remove
            </button>
          </div>
        </div>
      ))}
      <div className="cart-total" style={{
        fontSize: '1.25rem',
        fontWeight: 'bold',
        marginTop: '1rem',
        paddingTop: '1rem',
        borderTop: '2px solid #8B4513',
        textAlign: 'right'
      }}>
        Total: ${total.toFixed(2)}
      </div>
    </div>
  );
};

export default Cart;