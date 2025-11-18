import React from 'react';

const MenuItems = ({ menuItems, onAddToCart }) => {
  const groupedItems = menuItems.reduce((groups, item) => {
    const category = item.category;
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(item);
    return groups;
  }, {});

  return (
    <div>
      {Object.entries(groupedItems).map(([category, items]) => (
        <div key={category}>
          <h3 style={{ 
            color: '#8B4513', 
            borderBottom: '2px solid #D2691E', 
            paddingBottom: '0.5rem',
            marginTop: '2rem',
            marginBottom: '1rem'
          }}>
            {category}
          </h3>
          <div className="menu-grid">
            {items.map(item => (
              <div key={item.id} className="menu-item">
                <img 
                  src={item.image_url || 'https://via.placeholder.com/300x200?text=Delicious+Kabob'} 
                  alt={item.name}
                />
                <div className="menu-item-content">
                  <h3>{item.name}</h3>
                  <p>{item.description}</p>
                  <div className="price">${item.price.toFixed(2)}</div>
                  <button 
                    className="btn"
                    onClick={() => onAddToCart(item)}
                    disabled={!item.available}
                  >
                    {item.available ? 'Add to Cart' : 'Unavailable'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default MenuItems;