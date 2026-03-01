import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from dotenv import load_dotenv
from stock_data import check_conditions

load_dotenv()

app = Flask(__name__)

# Line Bot Configuration
configuration = Configuration(access_token=os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', ''))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET', ''))

# Simple in-memory watchlist. In a real app, use a database like SQLite or PostgreSQL.
watchlist = set(["2330", "2303"]) 

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature')
    if not signature:
        app.logger.error("Missing X-Line-Signature header")
        abort(400)

    # get request body as text
    body = request.get_data(as_text=True)
    
    # Quick fix for Line verification timeout: 
    # If the body is empty or just a verification check, return OK immediately.
    if not body or body == '{}':
        return 'OK'

    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text.strip().lower()
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        if text.startswith("add "):
            parts = text.split(" ")
            if len(parts) > 1:
                stock_id = parts[1]
                watchlist.add(stock_id)
                reply = f"✅ Added {stock_id} to watchlist."
            else:
                reply = "Please specify a stock ID, e.g., 'add 2330'"
        elif text.startswith("remove "):
            parts = text.split(" ")
            if len(parts) > 1:
                stock_id = parts[1]
                if stock_id in watchlist:
                    watchlist.remove(stock_id)
                    reply = f"❌ Removed {stock_id} from watchlist."
                else:
                    reply = f"⚠️ {stock_id} is not in watchlist."
            else:
                reply = "Please specify a stock ID, e.g., 'remove 2330'"
        elif text == "list":
            if watchlist:
                reply = "📋 Current watchlist:\n" + "\n".join(sorted(watchlist))
            else:
                reply = "📋 Watchlist is empty."
        elif text == "check":
            if not watchlist:
                reply = "📋 Watchlist is empty. Add stocks using 'add [stock_id]'."
            else:
                replies = []
                for stock_id in sorted(watchlist):
                    try:
                        is_met, msg = check_conditions(stock_id)
                        if is_met:
                            replies.append(msg)
                    except Exception as e:
                        replies.append(f"⚠️ Error checking {stock_id}: {str(e)}")
                
                if not replies:
                    reply = "📊 No stocks currently meet the advanced conditions (K > 20 cross + 3 days Foreign Net Buy)."
                else:
                    reply = "\n\n---\n\n".join(replies)
        else:
            reply = "Commands:\n- add [stock_id]\n- remove [stock_id]\n- list\n- check"

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

if __name__ == "__main__":
    app.run(host='localhost', port=8080, debug=False)
