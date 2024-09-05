



# FinanceTracker

---
**Finance Tracker** is a web application designed to help users keep track of their finances. With features like bank account management, paycheck tracking, and transaction history, it simplifies personal finance management. It also includes integration with Azure for analyzing receipts and automatically extracting receipt information.

## Features

- **Authentication & MFA**: Secure login system with multi-factor authentication (MFA) for added security.
- **Bank Accounts**: Manage multiple bank accounts, track balances, and associate transactions with specific accounts.
- **Paychecks**: Record and track paycheck information for detailed income history.
- **Transactions**: Log transactions for each account, including details like the amount, date, and description.
- **Azure Integration**: Automatically analyze receipts and extract relevant information using Azure Cognitive Services.
- **TailwindCSS UI**: Clean and responsive user interface built with TailwindCSS.
- **Deployed on DigitalOcean**: The app is hosted on DigitalOcean for reliable and scalable performance.


## Technology Stack

- **Backend**: Django
- **Authentication**: Django Allauth
- **Frontend**: TailwindCSS
- **Database**: SQLite (for development), PostgreSQL (for production)
- **Cloud Integration**: Azure Cognitive Services (for receipt analysis)
- **Deployment**: DigitalOcean (App Platform, Droplets)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/Tovborg/FinanceTracker.git
   cd FinanceTracker
   ```

2. Set up a virtual environment and install dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. Set up the `.env` file:

   Create a `.env` file in the root of your project with the necessary environment variables:

   ```
    DJANGO_SECRET_KEY=your_secret_key
    DJANGO_DEBUG=True
    ALLOWED_HOSTS=*
    MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN=True
    # Only if using PostgreSQL in production
    POSTGRES_DB=
    POSTGRES_USER=
    POSTGRES_PASSWORD=
    # Check settings.py for email configuration
    EMAIL_HOST_USER=
    EMAIL_HOST_PASSWORD=
    
    AZURE_KEY=
    AZURE_ENDPOINT=
   ```

4. Apply migrations:

   ```bash
   python manage.py migrate
   ```

5. Run the development server (use localhost to be able to use WebAuthn since 127.0.0.1 is considered insecure):

   ```bash
   python manage.py runserver localhost:3000
   ```

6. Access the app at `http://localhost:3000`.

## Usage

1. **Authentication**: Sign up or log in with MFA to secure your data.
2. **Add Bank Accounts**: Start by adding your bank accounts.
3. **Record Paychecks**: Keep track of your income by adding paychecks.
4. **Track Transactions**: Log transactions to maintain a detailed history of your spending and income.
5. **Upload Receipts**: Upload receipts and let Azure automatically analyze and extract the data for you.

## To-Do (Upcoming Features)

- [ ] **Budgeting Tool**: Add a feature to set and track monthly budgets for different categories (e.g., groceries, entertainment).
- [ ] **Recurring Transactions**: Allow users to set up recurring transactions such as bills or subscriptions.
- [ ] **Reporting Dashboard**: Provide users with customizable financial reports and insights.
- [ ] **Mobile App Integration**: Develop a mobile app to sync with the web version for on-the-go access.
- [ ] **Multi-Currency Support**: Enable users to track accounts and transactions in multiple currencies.
- [ ] **Notification System**: Send email or SMS notifications for important events (e.g., low balance, upcoming bills).
- [ ] **Dark Mode**: Add a dark mode option to the user interface.
- [ ] **Export Data**: Allow users to export their financial data to CSV or PDF for offline access.


## Contributing

Feel free to contribute by submitting issues or pull requests.






