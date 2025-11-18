import React, { useState, useEffect } from 'react';
import axios from 'axios';
import MenuItems from './components/MenuItems';
import Cart from './components/Cart';
import OrderForm from './components/OrderForm';
import OrderHistory from './components/OrderHistory';

const API_URL = process.env.REACT_APP_API_URL || '/api';

function App() {
  const [menuItems, setMenuItems] = useState([]);
  const [cart, setCart] = useState([]);
  const [currentView, setCurrentView] = useState('menu');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Debug currentView changes
  useEffect(() => {
    console.log('Current view changed to:', currentView);
  }, [currentView]);

  useEffect(() => {
    fetchMenuItems();
  }, []);

  const fetchMenuItems = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/menu`);
      setMenuItems(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching menu:', err);

      let errorMessage = 'Failed to load menu items. Please try again.';

      if (err.response) {
        const status = err.response.status;
        const data = err.response.data;

        if (status === 500) {
          errorMessage = 'Server error while loading menu.';
          if (data.detail) {
            errorMessage += ` ${data.detail}`;
          }
        } else if (status === 404) {
          errorMessage = 'Menu not found.';
        } else if (data.detail) {
          errorMessage = data.detail;
        }
      } else if (err.request) {
        errorMessage = 'Cannot connect to server. Please check your internet connection.';
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const addToCart = (item) => {
    setCart(prevCart => {
      const existingItem = prevCart.find(cartItem => cartItem.id === item.id);
      if (existingItem) {
        return prevCart.map(cartItem =>
          cartItem.id === item.id
            ? { ...cartItem, quantity: cartItem.quantity + 1 }
            : cartItem
        );
      }
      return [...prevCart, { ...item, quantity: 1 }];
    });
  };

  const removeFromCart = (itemId) => {
    setCart(prevCart => prevCart.filter(item => item.id !== itemId));
  };

  const updateCartQuantity = (itemId, quantity) => {
    if (quantity <= 0) {
      removeFromCart(itemId);
      return;
    }
    setCart(prevCart =>
      prevCart.map(item =>
        item.id === itemId ? { ...item, quantity } : item
      )
    );
  };

  const getCartTotal = () => {
    return cart.reduce((total, item) => total + (item.price * item.quantity), 0);
  };

  const clearCart = () => {
    setCart([]);
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="container">
          <h2>Loading delicious kabobs...</h2>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error">
        <div className="container">
          <h2>Oops! Something went wrong</h2>
          <p>{error}</p>
          <button className="btn" onClick={fetchMenuItems}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="header">
        <div className="container">
          <h1>🍢 Kabob Store</h1>
          <p>Authentic Mediterranean Flavors</p>
        </div>
      </header>

      <nav className="nav">
        <div className="container">
          <ul>
            <li>
              <a 
                href="#menu" 
                onClick={(e) => { e.preventDefault(); setCurrentView('menu'); }}
                style={{ 
                  backgroundColor: currentView === 'menu' ? 'rgba(255,255,255,0.2)' : 'transparent' 
                }}
              >
                Menu
              </a>
            </li>
            <li>
              <a 
                href="#order" 
                onClick={(e) => { e.preventDefault(); setCurrentView('order'); }}
                style={{ 
                  backgroundColor: currentView === 'order' ? 'rgba(255,255,255,0.2)' : 'transparent' 
                }}
              >
                Order ({cart.length})
              </a>
            </li>
            <li>
              <a 
                href="#orders" 
                onClick={(e) => { 
                  e.preventDefault(); 
                  console.log('Order History tab clicked, setting currentView to orders');
                  setCurrentView('orders'); 
                }}
                style={{ 
                  backgroundColor: currentView === 'orders' ? 'rgba(255,255,255,0.2)' : 'transparent' 
                }}
              >
                Order History
              </a>
            </li>
          </ul>
        </div>
      </nav>

      <main className="main">
        <div className="container">
          {currentView === 'menu' && (
            <>
              <h2>Our Delicious Menu</h2>
              <MenuItems 
                menuItems={menuItems} 
                onAddToCart={addToCart} 
              />
            </>
          )}

          {currentView === 'order' && (
            <>
              <h2>Your Order</h2>
              <Cart 
                cart={cart}
                onRemoveFromCart={removeFromCart}
                onUpdateQuantity={updateCartQuantity}
                total={getCartTotal()}
              />
              {cart.length > 0 && (
                <OrderForm 
                  cart={cart}
                  total={getCartTotal()}
                  onOrderComplete={clearCart}
                />
              )}
            </>
          )}

          {currentView === 'orders' && (
            <>
              {console.log('Rendering OrderHistory component')}
              <OrderHistory />
            </>
          )}
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          <p>&copy; 2025 Kabob Store. Serving authentic Mediterranean cuisine worldwide.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;