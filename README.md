# Chat Levels Bot 🤖🏆

A Telegram bot that tracks user activity and awards levels and XP based on participation.

## Features

- Tracks messages sent by users
- Awards XP for each message (1-3 XP)
- Levels up users when they reach certain XP thresholds
- Shows user rank with /rank command
- Displays leaderboard with /leaderboard command
- Persistent storage using Redis

## Deployment

### Heroku

1. Clone this repository
2. Create a new Heroku app
3. Add Redis addon (Heroku Redis)
4. Set environment variables:
   - `TELEGRAM_TOKEN` - Your bot token from @BotFather
5. Deploy to Heroku

### Local Development

1. Install requirements: `pip install -r requirements.txt`
2. Set up Redis locally or use Redis Cloud
3. Create a `.env` file with:
