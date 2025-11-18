from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
import re
import os
import boto3
from datetime import datetime, timedelta
import json
import threading
from urllib.parse import quote_plus
import uuid
import psycopg2
import psycopg2.extensions
from psycopg2.extras import RealDictCursor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("Using psycopg2 with AWS Aurora DSQL")

app = FastAPI(
    title="Kabob Store API",
    version="1.0.0",
    # Limit request body size to 1MB
    max_request_size=1_048_576
)

# Custom validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    # Sanitize error messages to avoid exposing internal details
    safe_errors = []
    for error in errors:
        safe_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"][1:]),
            "message": error["msg"],
            "type": error["type"]
        })
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": safe_errors}
    )

@app.middleware("http")
async def validate_request(request: Request, call_next):
    """Middleware to validate and sanitize incoming requests"""
    # Check for suspicious patterns in URL
    suspicious_patterns = [
        '../', '..\\',  # Path traversal
        '<script', '<%',  # XSS attempts
        'DROP TABLE', 'DELETE FROM',  # SQL injection attempts
        '\x00',  # Null byte
        'cmd=', 'exec(',  # Command injection
    ]

    path = str(request.url)
    for pattern in suspicious_patterns:
        if pattern.lower() in path.lower():
            logger.warning(f"Suspicious pattern detected in request: {pattern}")
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid request"}
            )

    # Check Content-Length for large requests
    content_length = request.headers.get('content-length')
    if content_length:
        try:
            size = int(content_length)
            if size > 1_048_576:  # 1MB limit
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large"}
                )
        except ValueError:
            pass

    response = await call_next(request)
    return response

DSQL_CLUSTER_IDENTIFIER = os.getenv("DSQL_CLUSTER_IDENTIFIER")
DATABASE_NAME = os.getenv("DATABASE_NAME", "kabobstore")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


# DSQL Connection Management
class DSQLConnectionManager:
    """Manages DSQL connections with automatic token refresh"""

    def __init__(self):
        self.connection = None
        self.token = None
        self.token_expires_at = None
        self.lock = threading.Lock()

    def get_fresh_token(self):
        """Generate a fresh DSQL authentication token using boto3"""
        dsql_endpoint = f"{DSQL_CLUSTER_IDENTIFIER}.dsql.{AWS_REGION}.on.aws"

        try:
            # Use boto3 DSQL client to generate token
            dsql_client = boto3.client('dsql', region_name=AWS_REGION)
            token = dsql_client.generate_db_connect_admin_auth_token(
                dsql_endpoint, AWS_REGION
            )

            # Tokens are valid for 1 hour, refresh 5 minutes early
            expires_at = datetime.now() + timedelta(minutes=55)

            return token, expires_at
        except Exception as e:
            logger.error(f"Failed to generate DSQL token: {e}")
            raise

    def get_connection(self):
        """Get psycopg2 connection with fresh token"""
        with self.lock:
            # Check if we need a new token/connection
            if (self.token is None or
                self.token_expires_at is None or
                datetime.now() >= self.token_expires_at or
                self.connection is None or
                self.connection.closed != 0):

                logger.info("Refreshing DSQL token and connection...")
                self.token, self.token_expires_at = self.get_fresh_token()
                logger.info(f"New token expires at: {self.token_expires_at}")

                # Close existing connection if any
                if self.connection and self.connection.closed == 0:
                    self.connection.close()

                # Create new connection with fresh token
                dsql_endpoint = f"{DSQL_CLUSTER_IDENTIFIER}.dsql.{AWS_REGION}.on.aws"

                self.connection = psycopg2.connect(
                    host=dsql_endpoint,
                    port=5432,
                    database="postgres",
                    user="admin",
                    password=self.token,
                    sslmode="require",
                    cursor_factory=RealDictCursor
                )
                # Use manual commit mode for better transaction control
                # self.connection.autocommit = False  # This is the default
            else:
                # If connection exists, ensure it's not in a failed transaction state
                try:
                    if self.connection.get_transaction_status() == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
                        logger.warning("Connection in failed transaction state, rolling back")
                        self.connection.rollback()
                except Exception as e:
                    logger.warning(f"Error checking transaction status: {e}")
                    # Try to rollback anyway
                    try:
                        self.connection.rollback()
                    except:
                        pass

            return self.connection

# Global connection manager
dsql_manager = DSQLConnectionManager()

def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize string input for additional safety"""
    if not value:
        return ""
    # Remove null bytes
    value = value.replace('\x00', '')
    # Truncate to max length
    value = value[:max_length]
    # Remove leading/trailing whitespace
    value = value.strip()
    return value

def validate_uuid_string(uuid_str: str) -> bool:
    """Validate UUID string format"""
    try:
        uuid.UUID(uuid_str)
        return True
    except (ValueError, AttributeError):
        return False

def ensure_tables_exist():
    """Ensure DSQL database tables exist

    Note: Aurora DSQL only allows 1 DDL statement per transaction,
    so we must commit after each CREATE TABLE.
    """
    conn = dsql_manager.get_connection()

    try:
        # Create menu_items table - DSQL allows only 1 DDL per transaction
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price NUMERIC(10, 2) NOT NULL,
                category VARCHAR(100) NOT NULL,
                image_url VARCHAR(500),
                available BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.close()
        conn.commit()  # Commit first DDL statement
        logger.info("Menu items table ensured")

        # Create orders table - separate transaction for second DDL
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id UUID PRIMARY KEY,
                customer_name VARCHAR(255) NOT NULL,
                customer_email VARCHAR(255) NOT NULL,
                items TEXT NOT NULL,
                total_amount NUMERIC(10, 2) NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.close()
        conn.commit()  # Commit second DDL statement
        logger.info("Orders table ensured")

        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to ensure DSQL tables exist: {e}")
        raise

def create_sample_menu_items():
    """Create sample menu items in a single transaction"""
    logger.info("Creating sample menu items...")

    sample_items = [
        ("Chicken Kabob", "Grilled chicken skewers with Mediterranean spices", 12.99, "Kabobs", "https://carlsbadcravings.com/wp-content/uploads/2023/06/Chicken-Kabobs-5.jpg"),
        ("Beef Kabob", "Tender beef cubes marinated in herbs", 14.99, "Kabobs", "https://www.recipetineats.com/tachyon/2018/07/Beef-Kabobs_2.jpg?resize=900%2C1260&zoom=1"),
        ("Lamb Kabob", "Succulent lamb with traditional seasonings", 16.99, "Kabobs", "https://www.acommunaltable.com/wp-content/uploads/2022/08/lamb-kebab-with-drizzle-1024x1536.jpeg"),
        ("Vegetable Kabob", "Fresh seasonal vegetables grilled to perfection", 9.99, "Kabobs", "https://www.veggiessavetheday.com/wp-content/uploads/2021/05/Grilled-Veggie-Kabobs-platter-1200x1800-1.jpg"),
        ("Hummus & Pita", "Creamy chickpea dip with olive oil", 6.99, "Appetizers", "https://images.squarespace-cdn.com/content/v1/5ed666a6924cd0017d343b01/1593544179725-1WMOUEETKOKCYY7JZ5FJ/bite-me-more-roasted-red-pepper-hummus-spiced-pita-chips-recipe.jpg?format=2500w"),
        ("Baklava", "Sweet pastry with nuts and honey", 4.99, "Desserts", "https://img.sndimg.com/food/image/upload/f_auto,c_thumb,q_55,w_860,ar_3:2/v1/img/recipes/59/86/3/Ye35HYGSEGgc0oGCIUag_Baklava-2.jpg")
    ]

    conn = dsql_manager.get_connection()
    cursor = conn.cursor()

    try:
        # Clear existing data first
        cursor.execute("DELETE FROM menu_items")
        logger.info("Cleared existing menu items")

        # Create sample items with parameterized queries
        for name, description, price, category, image_url in sample_items:
            item_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO menu_items (id, name, description, price, category, image_url, available)
                VALUES (%s::UUID, %s, %s, %s, %s, %s, %s)
            """, (item_id, name, description, price, category, image_url, True))
            logger.info(f"Created menu item: {name}")

        # Commit all changes together
        conn.commit()
        cursor.close()
        logger.info("Sample menu items created successfully and committed")

    except Exception as e:
        conn.rollback()
        cursor.close()
        logger.error(f"Failed to create sample menu items: {e}")
        raise


def get_menu_items():
    """Get all available menu items using raw SQL"""
    conn = dsql_manager.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, name, description, price, category, image_url, available, created_at
            FROM menu_items WHERE available = true
            ORDER BY category, name
        """)
        rows = cursor.fetchall()

        # RealDictCursor returns dictionaries, but we need to convert UUID and timestamp
        items = []
        for row in rows:
            items.append({
                'id': str(row['id']),
                'name': row['name'],
                'description': row['description'],
                'price': float(row['price']),
                'category': row['category'],
                'image_url': row['image_url'],
                'available': row['available'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            })

        # Commit the read transaction
        conn.commit()
        cursor.close()
        logger.info(f"Retrieved {len(items)} menu items from DSQL")
        return items

    except Exception as e:
        conn.rollback()
        cursor.close()
        logger.error(f"Failed to get menu items: {e}")
        # Return sample data as fallback
        return get_sample_menu_items()

def create_order(customer_name, customer_email, items, total_amount):
    """Create a new order within a transaction"""
    # Additional sanitization layer (already validated by Pydantic)
    customer_name = sanitize_string(customer_name, 255)
    customer_email = sanitize_string(customer_email, 255)

    if not customer_name or not customer_email:
        raise ValueError("Customer name and email are required")

    if not isinstance(items, list) or len(items) == 0:
        raise ValueError("Order must contain at least one item")

    if total_amount <= 0 or total_amount > 100000:
        raise ValueError("Invalid total amount")

    conn = dsql_manager.get_connection()
    cursor = conn.cursor()

    try:
        order_id = str(uuid.uuid4())

        logger.info(f"Creating order with ID: {order_id}")
        logger.info(f"Customer: {customer_name}, Email: {customer_email}")
        logger.info(f"Items: {items}, Total: {total_amount}")

        # First, check current order count
        cursor.execute("SELECT COUNT(*) FROM orders")
        count_before = cursor.fetchone()['count']
        logger.info(f"Orders count before insert: {count_before}")

        # Insert order with parameterized query to prevent SQL injection
        items_json = json.dumps(items)
        cursor.execute("""
            INSERT INTO orders (id, customer_name, customer_email, items, total_amount, status)
            VALUES (%s::UUID, %s, %s, %s, %s, %s)
        """, (order_id, customer_name, customer_email, items_json, total_amount, 'pending'))
        logger.info(f"Order INSERT executed for ID: {order_id}")

        # Check count after insert
        cursor.execute("SELECT COUNT(*) FROM orders")
        count_after = cursor.fetchone()['count']
        logger.info(f"Orders count after insert: {count_after}")

        # Try to retrieve the specific order by ID
        cursor.execute("""
            SELECT id, customer_name, customer_email, items, total_amount, status, created_at
            FROM orders WHERE id = %s::UUID
        """, (order_id,))
        row = cursor.fetchone()

        if not row:
            logger.warning(f"Order with ID {order_id} not found, checking most recent order")
            # Fallback: get the most recent order
            cursor.execute("""
                SELECT id, customer_name, customer_email, items, total_amount, status, created_at
                FROM orders ORDER BY created_at DESC LIMIT 1
            """)
            row = cursor.fetchone()

        if not row:
            raise Exception("Order was created but could not be retrieved - no orders in database")

        order_data = {
            'id': str(row['id']),
            'customer_name': row['customer_name'],
            'customer_email': row['customer_email'],
            'items': row['items'],
            'total_amount': float(row['total_amount']),
            'status': row['status'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None
        }

        # Commit the transaction
        conn.commit()
        cursor.close()
        logger.info(f"Order created and committed successfully: {order_data}")
        return order_data

    except Exception as e:
        conn.rollback()
        cursor.close()
        logger.error(f"Failed to create order: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise

def get_all_orders():
    """Get all orders using raw SQL"""
    conn = dsql_manager.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, customer_name, customer_email, items, total_amount, status, created_at
            FROM orders ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()

        # RealDictCursor returns dictionaries
        orders = []
        for row in rows:
            orders.append({
                'id': str(row['id']),
                'customer_name': row['customer_name'],
                'customer_email': row['customer_email'],
                'items': row['items'],
                'total_amount': float(row['total_amount']),
                'status': row['status'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            })

        # Commit the read transaction
        conn.commit()
        cursor.close()
        logger.info(f"Retrieved {len(orders)} orders from DSQL")
        return orders

    except Exception as e:
        conn.rollback()
        cursor.close()
        logger.error(f"Failed to get orders: {e}")
        return []

def get_sample_menu_items():
    """Return sample menu items as fallback with string UUIDs"""
    return [
        {
            'id': str(uuid.uuid4()),
            'name': 'Chicken Kabob',
            'description': 'Grilled chicken skewers with Mediterranean spices',
            'price': 12.99,
            'category': 'Kabobs',
            'image_url': 'https://carlsbadcravings.com/wp-content/uploads/2023/06/Chicken-Kabobs-5.jpg',
            'available': True,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Beef Kabob',
            'description': 'Tender beef cubes marinated in herbs',
            'price': 14.99,
            'category': 'Kabobs',
            'image_url': 'https://www.recipetineats.com/tachyon/2018/07/Beef-Kabobs_2.jpg?resize=900%2C1260&zoom=1',
            'available': True,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Lamb Kabob',
            'description': 'Succulent lamb with traditional seasonings',
            'price': 16.99,
            'category': 'Kabobs',
            'image_url': 'https://www.acommunaltable.com/wp-content/uploads/2022/08/lamb-kebab-with-drizzle-1024x1536.jpeg',
            'available': True,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Vegetable Kabob',
            'description': 'Fresh seasonal vegetables grilled to perfection',
            'price': 9.99,
            'category': 'Kabobs',
            'image_url': 'https://www.veggiessavetheday.com/wp-content/uploads/2021/05/Grilled-Veggie-Kabobs-platter-1200x1800-1.jpg',
            'available': True,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Hummus & Pita',
            'description': 'Creamy chickpea dip with olive oil',
            'price': 6.99,
            'category': 'Appetizers',
            'image_url': 'https://images.squarespace-cdn.com/content/v1/5ed666a6924cd0017d343b01/1593544179725-1WMOUEETKOKCYY7JZ5FJ/bite-me-more-roasted-red-pepper-hummus-spiced-pita-chips-recipe.jpg?format=2500w',
            'available': True,
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Baklava',
            'description': 'Sweet pastry with nuts and honey',
            'price': 4.99,
            'category': 'Desserts',
            'image_url': 'https://img.sndimg.com/food/image/upload/f_auto,c_thumb,q_55,w_860,ar_3:2/v1/img/recipes/59/86/3/Ye35HYGSEGgc0oGCIUag_Baklava-2.jpg',
            'available': True,
            'created_at': datetime.utcnow().isoformat()
        }
    ]





def initialize_database_with_sample_data():
    """Ensure database tables exist and have sample data"""
    try:
        # Always ensure tables exist (CREATE IF NOT EXISTS is safe to run)
        ensure_tables_exist()

        # Check if menu items exist
        conn = dsql_manager.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM menu_items")
            count = cursor.fetchone()['count']

            # Commit the SELECT query
            conn.commit()

            if count == 0:
                logger.info("No menu items found, creating sample data...")
                create_sample_menu_items()
            else:
                logger.info(f"Menu items already exist: {count} items")
        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close()

    except Exception as init_error:
        logger.error(f"Error during database initialization: {init_error}")
        raise

class MenuItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=1000)
    price: float = Field(..., gt=0, le=10000)
    category: str = Field(..., min_length=1, max_length=100)
    image_url: Optional[str] = Field(None, max_length=500)

    @validator('name', 'category')
    def validate_text_fields(cls, v):
        """Sanitize text fields to prevent XSS"""
        # Remove any HTML tags
        import re
        v = re.sub(r'<[^>]+>', '', v)
        # Remove extra whitespace
        v = ' '.join(v.split())
        if not v:
            raise ValueError('Field cannot be empty after sanitization')
        return v

    @validator('price')
    def validate_price(cls, v):
        """Ensure price is reasonable"""
        if v <= 0:
            raise ValueError('Price must be positive')
        if v > 10000:
            raise ValueError('Price exceeds maximum allowed value')
        # Round to 2 decimal places
        return round(v, 2)

    @validator('image_url')
    def validate_url(cls, v):
        """Validate image URL"""
        if v:
            if not v.startswith(('http://', 'https://')):
                raise ValueError('Image URL must start with http:// or https://')
            # Basic check for image extensions
            valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
            if not any(v.lower().endswith(ext) or f"{ext}?" in v.lower() for ext in valid_extensions):
                raise ValueError('URL must point to an image file')
        return v

class MenuItemResponse(BaseModel):
    id: str
    name: str
    description: str
    price: float
    category: str
    image_url: Optional[str]
    available: bool
    created_at: datetime

    class Config:
        from_attributes = True

class OrderItemCreate(BaseModel):
    id: str = Field(..., description="Menu item ID")
    name: str = Field(..., min_length=1, max_length=255)
    price: float = Field(..., gt=0, le=10000)
    quantity: int = Field(..., ge=1, le=100)

    @validator('id')
    def validate_uuid(cls, v):
        """Validate that ID is a proper UUID"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('Invalid UUID format')

class OrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255, description="Customer's full name")
    customer_email: EmailStr = Field(..., description="Valid email address")
    items: List[OrderItemCreate] = Field(..., min_items=1, max_items=50)

    @validator('customer_name')
    def validate_name(cls, v):
        """Validate customer name - only letters, spaces, hyphens, and apostrophes"""
        if not re.match(r"^[a-zA-Z\s\-']+$", v):
            raise ValueError('Name can only contain letters, spaces, hyphens, and apostrophes')
        # Remove extra spaces
        v = ' '.join(v.split())
        return v

    @validator('customer_email')
    def validate_email_domain(cls, v):
        """Additional email validation"""
        # Block disposable email domains (example list)
        blocked_domains = ['tempmail.com', 'throwaway.email', 'guerrillamail.com']
        domain = v.split('@')[1].lower()
        if domain in blocked_domains:
            raise ValueError('Disposable email addresses are not allowed')
        return v.lower()

    @validator('items')
    def validate_items(cls, v):
        """Validate order has unique items"""
        item_ids = [item.id for item in v]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError('Duplicate items in order. Please adjust quantities instead.')
        return v

class OrderResponse(BaseModel):
    id: str
    customer_name: str
    customer_email: str
    items: str
    total_amount: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/api/health")
def api_health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/api/menu", response_model=List[MenuItemResponse])
def get_menu():
    try:
        logger.info("Menu API called - retrieving menu items")
        menu_items = get_menu_items()
        logger.info(f"Successfully retrieved {len(menu_items)} menu items")
        return menu_items
    except Exception as e:
        logger.error(f"ERROR in get_menu: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/menu", response_model=MenuItemResponse)
def create_menu_item(item: MenuItemCreate):
    # For now, return sample response - can implement raw SQL insert later
    raise HTTPException(status_code=501, detail="Menu item creation not implemented in raw SQL mode")

@app.get("/api/menu/{item_id}", response_model=MenuItemResponse)
def get_menu_item(item_id: str):
    # For now, return sample response - can implement raw SQL select later
    raise HTTPException(status_code=501, detail="Individual menu item retrieval not implemented in raw SQL mode")

@app.post("/api/orders", response_model=OrderResponse)
def create_order_endpoint(order: OrderCreate):
    try:
        # Calculate total amount from validated items
        total_amount = sum(item.price * item.quantity for item in order.items)

        # Convert validated items to dict for storage
        items_dict = [
            {
                'id': item.id,
                'name': item.name,
                'price': item.price,
                'quantity': item.quantity
            }
            for item in order.items
        ]

        logger.info(f"Creating validated order for {order.customer_name} with total ${total_amount}")
        result = create_order(order.customer_name, order.customer_email, items_dict, total_amount)
        logger.info(f"Order created successfully: {result['id']}")
        return result
    except ValueError as e:
        # Validation errors
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"ERROR creating order: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

@app.get("/api/orders", response_model=List[OrderResponse])
def get_orders_endpoint():
    try:
        logger.info("Orders API called - retrieving all orders")
        orders = get_all_orders()
        logger.info(f"Successfully retrieved {len(orders)} orders")
        return orders
    except Exception as e:
        logger.error(f"ERROR in get_orders: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve orders: {str(e)}")

@app.get("/api/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):
    # For now, return error - can implement raw SQL select later
    raise HTTPException(status_code=501, detail="Individual order retrieval not implemented in raw SQL mode")

@app.post("/api/update-all-images")
def update_all_images():
    """Update all menu item images with new URLs"""
    # For now, return success message - images are already in sample data
    return {"message": "Images already updated in sample data"}

@app.delete("/api/orders/clear")
def clear_all_orders():
    """
    Delete all orders from the database

    WARNING: DEVELOPMENT ONLY - This endpoint is unprotected and allows anyone
    to delete ALL orders. In production, this must be:
    - Protected with authentication/authorization
    - Restricted to admin users only
    - Or removed entirely
    """
    conn = dsql_manager.get_connection()
    cursor = conn.cursor()

    try:
        # Delete all orders
        cursor.execute("DELETE FROM orders")

        # Commit the transaction
        conn.commit()
        cursor.close()
        logger.info("Deleted all orders from the database and committed")

        return {"message": "All orders deleted from the database"}

    except Exception as e:
        conn.rollback()
        cursor.close()
        logger.error(f"Error clearing orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear orders: {str(e)}")

@app.post("/api/initialize")
def initialize_database_endpoint():
    """
    Manually trigger database initialization

    WARNING: DEVELOPMENT ONLY - This endpoint is unprotected and allows anyone
    to trigger database initialization. While it won't destroy existing data,
    in production this should be:
    - Protected with authentication/authorization
    - Restricted to admin users only
    - Or removed entirely (rely on automatic initialization)
    """
    conn = dsql_manager.get_connection()
    cursor = conn.cursor()

    try:
        logger.info("Manual database initialization requested")

        # Just call the existing initialization function
        initialize_database_with_sample_data()

        # Get current counts for response
        cursor.execute("SELECT COUNT(*) FROM menu_items")
        menu_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()['count']

        # Commit the read transaction
        conn.commit()
        cursor.close()

        return {
            "message": "Database initialized successfully",
            "menu_items_count": menu_count,
            "orders_count": order_count
        }

    except Exception as e:
        conn.rollback()
        cursor.close()
        logger.error(f"Error initializing database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize database: {str(e)}")


@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    try:
        logger.info("Application starting - initializing database...")
        initialize_database_with_sample_data()
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}")
        # Continue anyway - will retry on first request

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)