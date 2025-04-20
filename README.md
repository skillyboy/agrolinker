# Agro Linker

Agro Linker is a comprehensive agricultural marketplace platform that connects farmers, buyers, and agricultural service providers. The platform facilitates seamless trading of agricultural products, provides logistics solutions, and offers financial services tailored for the agricultural sector.

## Features

- **User Management**
  - Multi-role authentication (Farmers, Buyers, Agents, Admins)
  - Profile management with verification system
  - Location-based services

- **Product Management**
  - Product listing and categorization
  - Quality grading system
  - Price tracking and analytics
  - Image management

- **Trading System**
  - Bidding and negotiation
  - Order management
  - Payment processing
  - Transaction history

- **Logistics**
  - Vehicle management
  - Delivery tracking
  - Route optimization
  - Status updates

- **Financial Services**
  - Mobile money integration
  - Loan management
  - Insurance services
  - Savings and thrift groups

- **Communication**
  - Real-time chat
  - SMS notifications
  - Email alerts
  - WhatsApp integration

## Technology Stack

- **Backend Framework**: Django 5.0.2
- **API Framework**: Django REST Framework 3.14.0
- **Database**: PostgreSQL (with psycopg2-binary)
- **Payment Processing**: Stripe
- **Image Processing**: Pillow
- **Production Server**: Waitress
- **Additional Tools**:
  - python-dotenv for environment management
  - django-cors-headers for CORS support
  - requests and aiohttp for HTTP operations

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/skillyboy/AgroLinker.git
   cd AgroLinker
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Update the variables with your configuration

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Project Structure

```
agro_linker/
├── api/                 # API endpoints and serializers
├── core/               # Core functionality
├── market/             # Marketplace features
├── orders/             # Order management
├── chat/               # Communication features
├── bid/                # Bidding system
├── weather/            # Weather integration
├── notification/       # Notification system
└── auth/               # Authentication system
```

## API Documentation

The API is organized into the following main endpoints:

- `/api/v1/market/` - Marketplace operations
- `/api/v1/orders/` - Order management
- `/api/v1/chat/` - Communication features
- `/api/v1/bid/` - Bidding system
- `/api/v1/weather/` - Weather information
- `/api/v1/notification/` - Notification system
- `/api/v1/auth/` - Authentication endpoints

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For any queries or support, please contact:
- GitHub: [@skillyboy](https://github.com/skillyboy) 
