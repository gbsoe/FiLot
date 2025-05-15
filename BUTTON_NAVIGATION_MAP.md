# FiLot Telegram Bot Button Navigation Map

This document provides a comprehensive map of all possible user journeys through the button-based navigation system of the FiLot Telegram bot. It captures all possible routes and scenarios users may encounter when interacting with the primary buttons: Invest, Explore, and Account.

## 1. Invest Button Navigation Routes

The Invest button serves as the primary entry point for investment-related actions, allowing users to view opportunities, set investment amounts, and manage their positions.

### Main Invest Menu Flow
- **Entry Point**: User clicks the "💰 Invest" button or types `/invest`
- **Initial Screen**: Shows investment options menu with predefined amounts
  ```
  🧠 Investment Recommendations
  
  Select an investment amount or view your current positions:
  ```

### 1.1 Pre-defined Amount Selection Flow
- **Trigger**: User selects a predefined amount ($100, $250, $500, $1,000, $5,000)
- **Route**: `amount_100`, `amount_250`, `amount_500`, `amount_1000`, `amount_5000`
- **Next Screen**: Shows top pool recommendations based on selected amount
- **User Options**:
  - **Select a pool**: Continues to pool detail view → `pool_recommendation_X`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 1.2 Custom Amount Flow
- **Trigger**: User selects "✏️ Custom Amount"
- **Route**: `amount_custom`
- **Next Screen**: Prompts user to enter a custom USD amount
- **User Inputs**: Any numeric value (e.g., "500", "$1000")
- **Next Screen**: Shows top pool recommendations based on custom amount
- **User Options**:
  - **Select a pool**: Continues to pool detail view → `pool_recommendation_X`
  - **Cancel**: Returns to invest menu → `menu_invest`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 1.3 View Positions Flow
- **Trigger**: User selects "👁️ View My Positions"
- **Route**: `menu_positions`
- **Possible States**:
  - **No positions**: Shows message that user has no active positions
  - **Has positions**: Lists all active positions with pool name, amount, and APR
- **User Options**:
  - **Select a position**: View position details → `position_detail_X`
  - **Back to Invest**: Returns to invest menu → `menu_invest`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 1.4 Pool Detail View
- **Trigger**: User selects a specific pool from recommendations
- **Route**: `pool_detail_X` (where X is the pool ID)
- **Next Screen**: Shows detailed information about the selected pool
- **User Options**:
  - **Invest in Pool**: Initiates investment process → `invest_in_pool_X`
  - **Back to Recommendations**: Returns to recommendation list → `back_to_recommendations`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 1.5 Exit Position Flow
- **Trigger**: User selects "Exit Position" from position detail view
- **Route**: `exit_position_X` (where X is the position ID)
- **Next Screen**: Confirmation dialog for exiting position
- **User Options**:
  - **Confirm Exit**: Processes position exit → `confirm_exit_X`
  - **Cancel**: Returns to position detail → `position_detail_X`
  - **Back to Positions**: Returns to positions list → `menu_positions`

### 1.6 Complete Investment Flow
- **Trigger**: User confirms investment in a pool
- **Route**: `confirm_invest_X_amount_Y` (where X is pool ID, Y is amount)
- **States**:
  - **Not connected to wallet**: Prompts wallet connection
  - **Connected to wallet**: Processes investment
- **Next Screen**: Investment confirmation or error message
- **User Options**:
  - **View Positions**: Goes to positions view → `menu_positions`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

## 2. Explore Button Navigation Routes

The Explore button allows users to browse available pools and simulate potential returns without committing to an investment.

### Main Explore Menu Flow
- **Entry Point**: User clicks the "🔍 Explore" button or types `/explore`
- **Initial Screen**: Shows exploration options
  ```
  🔍 Explore FiLot Opportunities
  
  What would you like to explore today?
  ```

### 2.1 Top Pools Flow
- **Trigger**: User selects "🏆 Top Pools"
- **Route**: `explore_pools`
- **Next Screen**: Lists top-performing liquidity pools
- **User Options**:
  - **Select a pool**: Views pool details → `pool_detail_X`
  - **Filter Options**: Shows filtering options → `filter_pools`
  - **Back to Explore Menu**: Returns to explore menu → `menu_explore`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 2.2 Simulate Returns Flow
- **Trigger**: User selects "📊 Simulate Returns"
- **Route**: `explore_simulate`
- **Next Screen**: Shows simulation amount options
- **User Options**:
  - **Select predefined amount**: Simulates with amount → `simulate_100`, `simulate_500`, `simulate_1000`, etc.
  - **Custom Amount**: Enters custom amount → `simulate_custom`
  - **Back to Explore Menu**: Returns to explore menu → `menu_explore`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 2.3 Pool Filtering Flow
- **Trigger**: User selects filter options from pool list
- **Route**: `filter_pools`
- **Options**:
  - **Sort by APR**: Sorts pools by APR → `sort_pools_apr`
  - **Sort by TVL**: Sorts pools by Total Value Locked → `sort_pools_tvl`
  - **Filter by Risk**: Filters by risk level → `filter_pools_risk_X`
  - **Reset Filters**: Clears all filters → `reset_filters`
  - **Back to Pool List**: Returns to unfiltered pool list → `explore_pools`

### 2.4 Simulation Results Flow
- **Trigger**: User completes simulation with an amount
- **Route**: From `simulate_X` or custom amount entry
- **Next Screen**: Shows projected returns for different pools
- **User Options**:
  - **View More Details**: Shows detailed breakdown → `simulation_detail_X`
  - **Invest This Amount**: Redirects to investment flow → `invest_amount_X`
  - **Try Different Amount**: Returns to simulation amount selection → `explore_simulate`
  - **Back to Explore Menu**: Returns to explore menu → `menu_explore`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 2.5 Pool Details from Explore
- **Trigger**: User selects a pool from the explore list
- **Route**: `pool_detail_X` (from explore context)
- **Next Screen**: Shows detailed information about the selected pool
- **User Options**:
  - **Simulate Investment**: Runs simulation for this pool → `simulate_pool_X`
  - **Invest Now**: Redirects to investment flow → `invest_in_pool_X`
  - **Back to Pool List**: Returns to pool list → `explore_pools`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

## 3. Account Button Navigation Routes

The Account button allows users to manage their account settings, wallet connections, and preferences.

### Main Account Menu Flow
- **Entry Point**: User clicks the "👤 Account" button or types `/account`
- **Initial Screen**: Shows account management options
  ```
  👤 Your Account
  
  Select an option below to manage your account:
  ```

### 3.1 Connect Wallet Flow
- **Trigger**: User selects "💼 Connect Wallet"
- **Route**: `account_wallet`
- **States**:
  - **Not connected**: Shows wallet connection options
  - **Already connected**: Shows current wallet with option to disconnect
- **User Options**:
  - **Connect via WalletConnect**: Initiates WalletConnect → `walletconnect`
  - **Enter Address Manually**: Prompts for manual address entry → `manual_wallet`
  - **Disconnect Wallet**: Removes connected wallet → `disconnect_wallet`
  - **Back to Account Menu**: Returns to account menu → `menu_account`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 3.2 Risk Profile Selection Flow
- **Trigger**: User selects a risk profile option
- **Routes**: `profile_high-risk` or `profile_stable`
- **Next Screen**: Confirmation of selected risk profile
- **User Options**:
  - **Change Profile**: Returns to profile selection → `account_profile`
  - **Back to Account Menu**: Returns to account menu → `menu_account`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 3.3 Subscription Management Flow
- **Trigger**: User selects "🔔 Subscribe" or "🔕 Unsubscribe"
- **Routes**: `account_subscribe` or `account_unsubscribe`
- **Next Screen**: Confirmation of subscription action
- **States**:
  - **Subscribe when not subscribed**: Confirms successful subscription
  - **Subscribe when already subscribed**: Shows already subscribed message
  - **Unsubscribe when subscribed**: Confirms successful unsubscription
  - **Unsubscribe when not subscribed**: Shows not subscribed message
- **User Options**:
  - **Back to Account Menu**: Returns to account menu → `menu_account`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 3.4 Help Section Flow
- **Trigger**: User selects "❓ Help"
- **Route**: `account_help`
- **Next Screen**: Shows help information and commands
- **User Options**:
  - **Back to Account Menu**: Returns to account menu → `menu_account`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 3.5 Status Information Flow
- **Trigger**: User selects "📊 Status"
- **Route**: `account_status`
- **Next Screen**: Shows system and user account status
- **Information Displayed**:
  - System status (Bot, CoinGecko, Raydium API)
  - User information (ID, subscription status, verification status, risk profile)
  - Account creation date
- **User Options**:
  - **Back to Account Menu**: Returns to account menu → `menu_account`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 3.6 Manual Wallet Connection Flow
- **Trigger**: User selects to enter wallet address manually
- **Route**: `manual_wallet`
- **Next Screen**: Prompts for Solana wallet address
- **User Inputs**: Solana wallet address (e.g., "5YourWalletAddressHere12345")
- **Next Screen**: Confirmation of wallet connection
- **User Options**:
  - **Back to Wallet Options**: Returns to wallet connection options → `account_wallet`
  - **Back to Account Menu**: Returns to account menu → `menu_account`
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

## 4. Universal Navigation Options

These navigation options are available throughout the bot interface and provide consistent ways for users to move between sections.

### 4.1 Back to Main Menu
- **Trigger**: User selects "🏠 Back to Main Menu" from any screen
- **Route**: `back_to_main`
- **Action**: Returns user to the main menu with primary options

### 4.2 Main Persistent Buttons
- **Always Available**: The bottom keyboard with main navigation buttons
  - "💰 Invest"
  - "🔍 Explore"
  - "👤 Account"
- **Action**: Directly navigates to the respective section regardless of current context

### 4.3 Command Shortcuts
- **Available Any Time**: Typed commands that override current context
  - `/start` - Restarts the bot interaction
  - `/help` - Shows help information
  - `/invest` - Goes to investment menu
  - `/explore` - Goes to exploration menu
  - `/account` - Goes to account menu

## 5. Error Handling Routes

These routes handle various error conditions and edge cases to ensure smooth user experience.

### 5.1 Session Timeout
- **Trigger**: User session times out due to inactivity
- **Action**: Shows timeout message with option to restart
- **User Options**:
  - **Restart Session**: Equivalent to /start command
  - **Continue**: Attempts to resume previous context if possible

### 5.2 API Connection Failures
- **Trigger**: Connection to external API (Raydium, CoinGecko) fails
- **Action**: Shows error message with appropriate guidance
- **User Options**:
  - **Retry**: Attempts operation again
  - **Back to Previous**: Returns to previous screen
  - **Back to Main Menu**: Returns to main menu → `back_to_main`

### 5.3 Wallet Connection Errors
- **Trigger**: Wallet connection fails or times out
- **Action**: Shows error message with troubleshooting steps
- **User Options**:
  - **Try Again**: Restarts wallet connection process
  - **Alternative Method**: Shows alternative connection methods
  - **Back to Account Menu**: Returns to account menu → `menu_account`

### 5.4 Invalid Input Handling
- **Trigger**: User provides invalid input (wrong format, out of range values)
- **Action**: Shows specific error message explaining issue
- **User Options**:
  - **Try Again**: Allows user to input again
  - **Cancel**: Returns to previous menu
  - **Help**: Shows guidance for correct input format

## 6. Context Switching Behavior

This section documents how the bot handles context switching between different navigation trees.

### 6.1 Direct Button Navigation
- When user clicks a main persistent button (Invest, Explore, Account), the bot:
  1. Saves current context if needed
  2. Clears any active temporary states
  3. Loads the selected main section fresh

### 6.2 Command Overrides
- When user types a command (e.g., /invest, /explore), the bot:
  1. Immediately switches to that command's context
  2. Discards any incomplete operations in progress
  3. Presents the main menu for the requested section

### 6.3 Back Navigation
- When user selects "Back" options, the bot:
  1. Returns to the previous logical screen
  2. Maintains any user selections or entered data where appropriate
  3. May clear temporary data if moving up multiple levels