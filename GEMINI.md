# Project: Taiwan Stock Monitor Line Bot

## Goal
A Line chatbot that monitors a watchlist of Taiwan stocks and sends notifications based on technical indicators and institutional investor data.

## Requirements
- **Watchlist**: Support managing a list of stock symbols to monitor.
- **K-Value Notification**:
    - Notify when the **K value** (from KD indicator) crosses **20** from low to high (K > 20).
- **Advanced Filter**:
    - Notify when **K > 20** AND **Foreign investors have a net buy for 3 consecutive days**.
- **Platform**: Line Messaging API.

## Technical Considerations (To be researched)
- **Stock Data**: Sources for Taiwan stock price and KD indicator data (e.g., Yahoo Finance, Fugle, or FinMind).
- **Institutional Data**: Sources for Foreign investors net buy/sell data (e.g., TWSE).
- **Line Bot**: Setup Line Messaging API, webhook, and potentially a database for the watchlist.
