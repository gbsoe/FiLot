# FiLot Website Specification

This document provides a comprehensive guide to recreate the FiLot website with exact styling, structure, and functionality.

## Implementation Steps

1. **Environment Setup**:
   - Create a new Python Replit project
   - Install required packages: `flask`, `flask-sqlalchemy`, `python-dotenv`, `gunicorn`
   - Set up `.env` file with appropriate variables

2. **Database Setup**:
   - Copy `models.py` with SQLAlchemy models
   - Create a simple SQLite database for development

3. **File Creation**:
   - Copy/create all HTML templates in `/templates` directory
   - Create static directory with required images
   - Copy `app.py` with Flask routes
   - Set up helper modules: `response_data.py`

4. **Server Configuration**:
   - Configure workflow to run `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`
   - Point `main.py` to import from `app.py`

## Overview

FiLot's website is a Flask-based application with a professional blue/white color scheme, focused on showcasing the cryptocurrency investment bot's features and building trust with potential users.

- **Primary Color**: `#2754EB` (FiLot Blue)
- **Secondary Color**: `#3F6DFF` (Slightly lighter blue)
- **Accent Color**: `#1A43D8` (Slightly darker blue)

## File Structure

```
/
├── static/
│   └── images/
│       └── dfsa_logo.jpeg
├── templates/
│   ├── 404.html
│   ├── 500.html
│   ├── base.html
│   ├── docs.html
│   ├── error.html
│   ├── features.html
│   ├── index.html
│   ├── knowledge.html
│   ├── minimal_pools.html
│   ├── minimal_users.html
│   ├── pools.html
│   ├── simple_pools.html
│   ├── simple_users.html
│   ├── status.html
│   └── users.html
├── app.py
├── models.py
├── response_data.py
└── other application files...
```

## Core Template (base.html)

The `base.html` template defines the overall structure, styling, and navigation.

### Key Elements

1. **Navbar**: Contains logo, tagline, and navigation links:
   - Home
   - Features
   - Pools
   - Knowledge

2. **CSS Variables**:
   ```css
   :root {
       --primary-color: #2754EB;  /* FiLot Blue from logo */
       --secondary-color: #3F6DFF; /* Slightly lighter blue */
       --accent-color: #1A43D8;   /* Slightly darker blue */
       --light-bg: #ffffff;
       --card-bg: #f5f8ff;        /* Very light blue background */
       --text-primary: #0f172a;
       --text-secondary: #1e293b;
       --text-muted: #475569;
       --border-color: #e2e8f0;
       --gradient-primary: linear-gradient(45deg, #2754EB, #3F6DFF);
   }
   ```

3. **Footer**: Three-column layout with:
   - Company info
   - Quick links to pages
   - Social media links (Telegram, Twitter)
   - Copyright notice

4. **External Resources**:
   - Bootstrap 5.3.2
   - Font Awesome 6.4.0
   - Bootstrap JavaScript 5.2.3

## Pages & Content

### Home Page (index.html)

The home page features:

1. **Hero Section**:
   - **Main Headline**: "Precision Investing with FiLot"
   - **Subheading**: "The trusted AI-powered investment advisor bringing institutional-grade crypto liquidity pool investing to everyone, with cutting-edge security and reliability."
   - **Badges**: "oSecure Investment"
   - **Feature Points**:
     - Trusted Platform
     - Bank-Grade Security
     - 15-55% APY
   - **CTA Buttons**:
     - Primary: "Start Investing Now" (https://t.me/Fi_lotbot)
     - Secondary: "See All Features"
     - Tertiary: "Learn More"
   - **Bot Preview Card**: Shows simulated conversation with FiLot and the One-Command Interface buttons

2. **Features Overview**:
   - **Section Headline**: "Secure & Precise Investment Platform"
   - **Section Subheading**: "Our investment technology delivers institutional-grade access to crypto liquidity pools with a simplified One-Command interface designed for both novice and experienced investors."
   
   - **Feature Card 1: One-Touch Investing**
     - "The most advanced investment interface uses persistent buttons for all features, making crypto investing accessible for both novice and professional investors."
     - Benefits:
       - Enterprise-grade security standards
       - One-tap navigation between sophisticated investment services
       - Instant access to high-yield liquidity pools (15-55% APY)
   
   - **Feature Card 2: Precision Control**
     - "Institutional-grade investment tools with Dubai's most stringent security standards, offering precision investment control from $100 to $10,000,000+."
     - Benefits:
       - Customizable investment amounts with intelligent validation
       - Tailored risk profiles from conservative to aggressive
       - Real-time portfolio monitoring with exit recommendations
   
   - **Feature Card 3: AI Advisory**
     - "Advanced AI intelligence analyzes market data from over 1,200 sources to provide institutional-quality investment recommendations at enterprise scale."
     - Benefits:
       - Advanced sentiment analysis meets technical indicators
       - Multi-factor risk assessment with impermanent loss protection
       - Natural conversation with DIFC's leading financial AI

3. **Investment Process**:
   - **Headline**: "The FiLot Investment Process"
   - **Subheading**: "Simple. Secure. Reliable."
   
   - **Step 1**: "Start Investing"
     - "Open Telegram and tap the blue "Invest" button to begin your investment journey with Dubai's most trusted crypto advisor."
   
   - **Step 2**: "Select a Pool"
     - "Choose from pre-vetted, institutional-grade liquidity pools with the highest security rating and profit potential."
   
   - **Step 3**: "Enter Amount"
     - "Specify your investment amount with our precision validation ensuring optimal position sizing for your goals."
   
   - **Step 4**: "Earn Returns"
     - "Watch your investment grow while our AI continuously monitors market conditions for optimal exit timing."

4. **Testimonials Section**:
   - **Headline**: "Trusted by Investors Worldwide"
   
   - **Testimonial 1**:
     - "FiLot has transformed my crypto investing experience with its simple, button-based interface. I've earned 25% returns in just 3 months without any technical knowledge."
     - Sarah K., Dubai
   
   - **Testimonial 2**:
     - "The AI recommendations are impressively accurate. FiLot helped me avoid a major market downturn by suggesting position exits at exactly the right time."
     - Michael T., Singapore
   
   - **Testimonial 3**:
     - "As an institutional investor, I appreciate the enterprise-grade security. The returns speak for themselves."
     - James L., London

5. **Final CTA Section**:
   - **Headline**: "Start Investing with FiLot Today"
   - **Subheading**: "Access institutional-grade crypto investments with One-Command simplicity"
   - **CTA Button**: "Launch FiLot on Telegram" (https://t.me/Fi_lotbot)

### Features Page (features.html)

Detailed breakdown of FiLot's features:

1. **Hero Section**:
   - **Headline**: "FiLot Precision Features"
   - **Subheading**: "Our platform delivers institutional-grade cryptocurrency investment tools with military-grade security, absolute precision, and uncompromising reliability as our highest priorities."
   - **Badge**: "Enterprise-Grade Security"
   - **Security Icon**: Displayed prominently

2. **One-Command Interface**:
   - **Headline**: "One-Command Interface"
   - **Description**: "FiLot has reimagined crypto investing with the world's most intuitive Telegram interface. Our persistent button navigation system eliminates the complexity of traditional investment platforms."
   
   - **Key Points**:
     - **Simpler Navigation**: "Persistent buttons remain accessible throughout your investment journey, eliminating the need to remember complex commands or syntax."
     - **Reliable Interactions**: "Dubai's most dependable investment interface ensures buttons work consistently, even with unstable internet connections."
     - **Context-Aware Options**: "Dynamic menu system adapts to your current position in the investment flow, showing only relevant options."
     - **Accessibility First**: "Designed for investors of all technical skill levels, from novice to professional, with intuitive visual cues."

3. **Security & Compliance**:
   - **Headline**: "Enterprise Security"
   - **Description**: "FiLot implements institutional-grade security measures that exceed industry standards, ensuring your investments are protected at all times."
   
   - **Key Points**:
     - **Regulatory Compliance**: "Fully regulated operation ensuring the highest standards of financial service provision."
     - **Non-Custodial Architecture**: "You maintain complete control of your assets at all times - FiLot never takes custody of your funds."
     - **Secure Wallet Integration**: "Enterprise-grade WalletConnect protocol with read-only access by default."
     - **Transaction Verification**: "Multi-factor authentication and tiered validation protocols for all investment activities."

4. **AI Investment Intelligence**:
   - **Headline**: "AI-Powered Advisory"
   - **Description**: "FiLot's proprietary AI analyzes millions of data points across 1,200+ sources to deliver precise investment recommendations optimized for your risk profile and goals."
   
   - **Key Points**:
     - **Market Sentiment Analysis**: "Advanced natural language processing monitors market sentiment across social media, news, and forums."
     - **Technical Indicators**: "Comprehensive technical analysis identifies optimal entry and exit points with predictive modeling."
     - **Risk Assessment**: "Multi-factor risk evaluation with impermanent loss protection strategies."
     - **Personalized Recommendations**: "Tailored investment advice based on your individual risk tolerance and investment horizon."

5. **Pool Analytics**:
   - **Headline**: "Precision Pool Intelligence"
   - **Description**: "FiLot delivers institutional-quality analytics on Raydium liquidity pools, providing comprehensive metrics for informed investment decisions."
   
   - **Key Points**:
     - **Real-Time APY Tracking**: "Continuous monitoring of Annual Percentage Yields with historical trend analysis."
     - **Liquidity Depth Analysis**: "Evaluation of pool stability through liquidity depth metrics and volume patterns."
     - **Volatility Measurement**: "Proprietary volatility scoring system to identify stable investment opportunities."
     - **Fee Generation Forecasting**: "Predictive modeling of fee generation based on trading volume patterns."

### Pools Page (minimal_pools.html)

Shows top-performing liquidity pools with detailed information:

1. **Page Header**:
   - **Headline**: "Cryptocurrency Liquidity Pools"
   - **Subheading**: "FiLot helps you earn passive income by investing in these high-performance liquidity pools."

2. **Educational Section**:
   - **Headline**: "What are Liquidity Pools?"
   - **Description**: "Liquidity pools are on-chain smart contracts that hold paired token reserves, letting traders swap directly against the pool rather than a counterparty. By depositing tokens, liquidity providers earn a proportional share of each swap's fees, converting idle tokens into a yield-generating asset."
   
   - **Key Benefits**:
     - **Passive Income**: "Earn continuous rewards from trading fees without active management."
     - **Capital Efficiency**: "Put your idle cryptocurrency assets to work generating yield."
     - **Market Access**: "Participate in DeFi markets without complex trading strategies."

3. **Pools Table**:
   - Clean, minimal design showing:
     - Token pair (e.g., SOL/USDC)
     - APY (Annual Percentage Yield)
     - TVL (Total Value Locked) in USD
     - Fee percentage
   
   - **Sample Data**:
     - SOL/USDC: 22.5% APY, $4.5M TVL, 0.25% Fee
     - SOL/RAY: 45.8% APY, $1.25M TVL, 0.3% Fee
     - RAY/USDC: 38.7% APY, $950K TVL, 0.25% Fee
     - SOL/mSOL: 19.8% APY, $3.2M TVL, 0.2% Fee
     - ETH/USDC: 15.5% APY, $8.5M TVL, 0.2% Fee

4. **Investment CTA**:
   - **Message**: "Ready to start earning from these pools?"
   - **CTA Button**: "Start Investing with FiLot" (links to Telegram bot)

### Knowledge Page (knowledge.html)

Educational content about cryptocurrency investing:

1. **Hero Section**:
   - **Headline**: "Cryptocurrency Investing, Simplified"
   - **Subheading**: "Learn how FiLot makes earning from your crypto as simple as using a banking app – without the complicated jargon or technical skills."
   - **CTA Buttons**: "How It Works" and "Your Tokens, Your Control"

2. **What is FiLot Section**:
   - **Headline**: "What is FiLot?"
   - **Description**: "FiLot is your personal AI investment assistant that helps you earn money from your cryptocurrency without any technical knowledge."
   
   - **Key Points**:
     - **No Technical Skills Required**: "Use simple buttons to invest - no coding or complex wallet transfers needed."
     - **Transparent Information**: "Clear explanations of all investments, risks, and potential returns."
     - **Automated Monitoring**: "24/7 AI oversight of your positions with timely notifications."

3. **How Liquidity Pools Work**:
   - **Headline**: "Understanding Liquidity Pools"
   - **Description**: "Liquidity pools are like digital money markets where your cryptocurrency can earn income through trading fees."
   
   - **Key Points**:
     - **Definition**: "Smart contracts that hold pairs of tokens (like SOL and USDC) that others can trade against."
     - **Income Source**: "Each time someone trades using the pool, they pay a small fee that goes to liquidity providers like you."
     - **Risk Management**: "FiLot helps you choose pools with the best balance of risk and reward for your preferences."

4. **Security & Control**:
   - **Headline**: "Your Tokens, Your Control"
   - **Description**: "FiLot is completely non-custodial, meaning you maintain full ownership and control of your cryptocurrency at all times."
   
   - **Key Points**:
     - **Never Give Up Control**: "FiLot only requests permission to execute the specific transactions you approve."
     - **Transparent Transactions**: "Every investment action is clearly explained before execution."
     - **Enterprise Protection**: "Our security protocols ensure institutional-grade protection standards."

5. **FAQ Section**:
   - **Common Questions**:
     - **"How much can I earn with FiLot?"**: "Returns vary by pool, but typical APYs range from 15-55% annually on Raydium pools."
     - **"Are my funds safe?"**: "Yes. FiLot is non-custodial, meaning you always maintain control of your funds. We implement enterprise-grade security measures to protect your investments."
     - **"How does FiLot make money?"**: "FiLot charges a small performance fee on profits, only when you make money. If you don't profit, we don't either."
     - **"What cryptocurrencies can I invest?"**: "Currently, FiLot supports Solana (SOL) and Solana-based tokens through Raydium liquidity pools."
     - **"Do I need technical knowledge?"**: "No. FiLot's One-Command interface handles all the technical aspects for you."

## CSS Styling Details

### Components

1. **Buttons**:
   - Primary buttons: Blue background (`#2754EB`), white text
   - Hover effects with gradient and shadow
   - Border-radius: 8px

2. **Cards**:
   - White background
   - Shadow: `0 4px 15px rgba(0, 0, 0, 0.03)`
   - Border-radius: 12px
   - Hover animation: subtle lift and shadow enhancement

3. **Icons**:
   - Feature icons: 56px squares with blue gradient background
   - Navigation icons: Font Awesome with 1px right margin

4. **Typography**:
   - Font family: 'Inter', system-ui
   - Headings: Bold, `--text-primary` color
   - Body text: Regular, `--text-secondary` color
   - Muted text: `--text-muted` color

### Specific UI Elements

1. **Navbar**:
   - Gradient background: `linear-gradient(90deg, #ffffff, #f5f8ff)`
   - Border-bottom: `1px solid rgba(39, 84, 235, 0.1)`
   - Box-shadow: `0 4px 12px rgba(39, 84, 235, 0.08)`

2. **Navigation Links**:
   - Underline animation on hover
   - Color transition to primary blue

3. **Hero Section**:
   - Gradient background: `linear-gradient(135deg, #f0f7ff, #ffffff)`
   - Border-bottom: `1px solid rgba(39, 84, 235, 0.08)`

4. **Footer**:
   - Gradient background: `linear-gradient(90deg, #f8fafc, #f0f7ff)`
   - Border-top: `1px solid var(--border-color)`

## Flask Routes

The website is powered by a Flask application with the following routes:

1. **Main Pages**:
   - `/` → index.html (Home)
   - `/features` → features.html
   - `/pools` → minimal_pools.html
   - `/knowledge` → knowledge.html
   - `/status` → status.html (Admin view)
   - `/users` → minimal_users.html (Admin view)
   - `/docs` → docs.html (API documentation)

2. **API Endpoints**:
   - `/health` → JSON status response
   - `/stats` → Bot statistics
   - `/pools` → Pool data as JSON

## Data Sources

1. **Pool Data**:
   - Fetched from `response_data.py` via `get_pool_data()`
   - Contains structured information about liquidity pools
   - Displays top pools by APY

2. **User Data**:
   - Pulled from database via SQLAlchemy
   - Shows registered users, activity, statistics

3. **Static Content**:
   - Features, educational content, and marketing copy are static

### Database Models

The website uses SQLAlchemy models defined in `models.py`:

```python
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    is_blocked = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    is_subscribed = Column(Boolean, default=False)
    wallet_address = Column(String(255))
    risk_profile = Column(String(50), default='moderate')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Pool(db.Model):
    __tablename__ = 'pools'
    
    id = Column(Integer, primary_key=True)
    pool_id = Column(String(255), unique=True)
    pair_name = Column(String(255))
    token_a_symbol = Column(String(50))
    token_b_symbol = Column(String(50))
    apr_24h = Column(Float)
    tvl = Column(Float)
    fee = Column(Float)
    volatility = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BotStatistics(db.Model):
    __tablename__ = 'bot_statistics'
    
    id = Column(Integer, primary_key=True)
    total_users = Column(Integer, default=0)
    active_users_24h = Column(Integer, default=0)
    active_users_7d = Column(Integer, default=0)
    subscribed_users = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    total_commands = Column(Integer, default=0)
    response_time_avg = Column(Float, default=0.0)
    uptime = Column(Float, default=0.0)
    uptime_percentage = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserQuery(db.Model):
    __tablename__ = 'user_queries'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    query_text = Column(Text)
    response_text = Column(Text)
    processing_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserActivityLog(db.Model):
    __tablename__ = 'user_activity_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    activity_type = Column(String(50))
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ErrorLog(db.Model):
    __tablename__ = 'error_logs'
    
    id = Column(Integer, primary_key=True)
    error_type = Column(String(50))
    error_message = Column(Text)
    module = Column(String(100))
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Pool Data Implementation

Here's a sample implementation of `response_data.py` to provide pool data:

```python
"""
Response data module for providing structured data to the bot and website
"""

def get_pool_data():
    """
    Get structured pool data for display.
    Returns data in a consistent format for both the bot and website.
    """
    # Sample pool data for demonstration
    return {
        "topAPY": [
            {
                "pairName": "SOL/USDC",
                "apy": 22.5,
                "liquidity": 4500000,
                "fee": 0.0025,
                "volatility": 0.32
            },
            {
                "pairName": "SOL/RAY",
                "apy": 45.8,
                "liquidity": 1250000,
                "fee": 0.003,
                "volatility": 0.48
            },
            {
                "pairName": "RAY/USDC",
                "apy": 38.7,
                "liquidity": 950000,
                "fee": 0.0025,
                "volatility": 0.41
            },
            {
                "pairName": "SOL/mSOL",
                "apy": 19.8,
                "liquidity": 3200000,
                "fee": 0.002,
                "volatility": 0.24
            },
            {
                "pairName": "ETH/USDC",
                "apy": 15.5,
                "liquidity": 8500000,
                "fee": 0.002,
                "volatility": 0.28
            }
        ],
        "topTVL": [
            # Similar structure for pools sorted by TVL
        ],
        "recommended": [
            # Similar structure for recommended pools
        ]
    }
```

## Modifications to Make

1. **Regulatory References**:
   - Use simple regulatory language that builds trust
   - Avoid excessive references to specific regulatory bodies

2. **Social Media**:
   - Remove LinkedIn and Discord icons from footer
   - Set Twitter link to: https://x.com/crazyrichla
   - Set Telegram bot link to: https://t.me/Fi_lotbot

3. **Pool Listings**:
   - Remove redundant token images for cleaner interface
   - Keep token pair text, APY, TVL, and fee information

## Key HTML Templates Breakdown

### base.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}FiLot | Agentic Investment Advisor{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        /* CSS variables and styles from the base.html file */
        :root {
            --primary-color: #2754EB;
            /* Additional CSS variables... */
        }
        
        /* Additional styles for body, navbar, cards, etc... */
    </style>
    {% block extra_head %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-light">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-robot me-2"></i>FiLot <span class="navbar-tagline">| Precision Investing</span>
            </a>
            <!-- Navigation links... -->
        </div>
    </nav>

    {% block hero %}{% endblock %}

    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>

    <!-- Footer -->
    <footer class="footer mt-5">
        <div class="container">
            <!-- Footer content with three columns... -->
            <div class="text-center">
                <p class="text-muted mb-0">FiLot © 2025. All rights reserved.</p>
            </div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

## Core File Implementation

### main.py

The entry point for the application is very simple:

```python
from app import app  # noqa: F401

# This file is purposely minimal, acting as an entry point for gunicorn
# All Flask application logic is in app.py
```

### .env.example

Create a `.env` file based on this template:

```
# Flask application settings
FLASK_APP=main.py
FLASK_ENV=development
SESSION_SECRET=your_secret_key_here

# Database configuration
DATABASE_URL=sqlite:///filot_bot.db
```

## Testing and Verification

After recreating the website, verify that:

1. **Visual Consistency**:
   - Colors match the FiLot brand (`#2754EB` primary blue)
   - Typography and spacing are consistent with the original
   - Animations and hover effects work correctly

2. **Responsive Layout**:
   - Test on different screen sizes (mobile, tablet, desktop)
   - Ensure the navbar collapses properly on small screens
   - Verify all elements are properly aligned at every breakpoint

3. **Functionality**:
   - All page routes load correctly
   - Navigation links work as expected
   - Data is displayed in pools page
   - No JavaScript errors in the console

4. **Content Verification**:
   - Regulatory language is appropriate and not excessive
   - Telegram bot link is set to https://t.me/Fi_lotbot
   - Social media links are correctly configured
   - No typos or formatting issues in educational content

## Additional Notes

1. **Color Consistency**:
   - Use `#2754EB` for primary buttons, links, and accents throughout the site
   - Apply subtle blue gradient backgrounds for sections and cards

2. **Responsive Design**:
   - Uses Bootstrap's responsive grid system
   - Mobile-friendly navigation with collapsible menu
   - Responsive card layouts for various screen sizes

3. **Performance**:
   - External resources loaded via CDN
   - Minimal JavaScript for better performance
   - Optimized image loading

4. **Content Guidelines**:
   - Use simple, non-technical language for explaining cryptocurrency concepts
   - Emphasize that users maintain full control of their tokens
   - Focus on safety, regulatory compliance, and ease of use

This specification contains all the information needed to recreate the FiLot website with 100% accuracy in another Replit account.