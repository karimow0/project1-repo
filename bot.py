import psycopg2
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Load environment variables
load_dotenv('tel_token.env')
TOKEN: Final = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_USERNAME: Final = '@EnroLLAI_bot'

app = Flask(__name__)

# Database connection function
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

# Fetch answer for a question
def get_faq_answer(question):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT answer FROM faq WHERE question = %s", (question,))
            result = cursor.fetchone()
            return result[0] if result else "Sorry, no answer found."
    except Exception as e:
        print(f"Database Error: {e}")
        return "An error occurred while fetching the answer."
    finally:
        if conn:
            conn.close()

# Fetch FAQ categories
def get_faq_categories():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT category FROM faq")
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Database Error: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Fetch questions by category
def get_faq_questions_by_category(category):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT question FROM faq WHERE category = %s", (category,))
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Database Error: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Webhook for Dialogflow integration
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    query = data['queryResult']['queryText']
    answer = get_faq_answer(query)
    return jsonify({'fulfillmentText': answer})

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome to EnroLLAI! Type /help to see available commands.')

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Here are the available commands:\n"
        "/enroll - Get information about enrollment\n"
        "/FAQ - Get answers to frequently asked questions\n"
    )
    await update.message.reply_text(help_text)

# Enroll command
async def enroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    enroll_text = (
        "To enroll in an Italian university:\n"
        "1️⃣ Choose a university and program.\n"
        "2️⃣ Prepare your documents (passport, diploma, transcript, etc.).\n"
        "3️⃣ Apply through Universitaly or directly on the university website.\n"
        "4️⃣ Wait for admission results and apply for a visa.\n"
        "Need help? Ask me!"
    )
    await update.message.reply_text(enroll_text)

# FAQ command
async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categories = get_faq_categories()
    if categories:
        keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in categories]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please choose a category:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("No FAQ categories available.")

# Button callback for categories and questions
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data
    questions = get_faq_questions_by_category(category)
    if questions:
        numbered_questions = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        await query.message.reply_text(f"Questions in '{category}':\n{numbered_questions}")
    else:
        await query.message.reply_text("No questions found in this category.")

# Answering questions by number
async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    try:
        question_number = int(user_input) - 1
        category = context.user_data.get("selected_category")
        if category:
            questions = get_faq_questions_by_category(category)
            if 0 <= question_number < len(questions):
                answer = get_faq_answer(questions[question_number])
                await update.message.reply_text(answer)
            else:
                await update.message.reply_text("Invalid question number. Please try again.")
        else:
            await update.message.reply_text("Please select a category first using /FAQ.")
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")

# Main function to run the bot
def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('enroll', enroll_command))
    application.add_handler(CommandHandler('FAQ', faq_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer_question))

    print('Bot is running!')
    application.run_polling()

if __name__ == '__main__':
    main()













