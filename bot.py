import psycopg2
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Load environment variables
load_dotenv('tel_token.env')
TOKEN: Final = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_USERNAME: Final = '@EnroLLAI_bot'

app = Flask(__name__)

# Database functions
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

def get_faq_answer(question):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT answer FROM faq WHERE question = %s", (question,))
        result = cursor.fetchone()
        print(f"Answer for question '{question}': {result}")  # Debugging
        return result[0] if result else "Sorry, no answer found."
    except Exception as e:
        print(f"Database Error: {e}")
        return "An error occurred while fetching the answer."
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_faq_categories():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM faq")
        categories = [row[0] for row in cursor.fetchall()]
        return categories
    except Exception as e:
        print(f"Database Error: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_faq_questions_by_category(category):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT question FROM faq WHERE category = %s", (category,))
        questions = [row[0] for row in cursor.fetchall()]
        print(f"Questions in category '{category}': {questions}")  # Debugging
        return questions
    except Exception as e:
        print(f"Database Error: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Flask Webhook for Dialogflow Integration
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    query = data['queryResult']['queryText']
    answer = get_faq_answer(query)
    return jsonify({'fulfillmentText': answer})

# Telegram Bot Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome to EnroLLAI! Type /help to see available commands.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "Here are the available commands:\n"
    help_text += "/enroll - Get information about enrollment\n"
    help_text += "/FAQ - Get answers to frequently asked questions\n"
    await update.message.reply_text(help_text)

async def enroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    enroll_text = "To enroll in an Italian university:\n"
    enroll_text += "1️⃣ Choose a university and program.\n"
    enroll_text += "2️⃣ Prepare your documents (passport, diploma, transcript, etc.).\n"
    enroll_text += "3️⃣ Apply through Universitaly or directly on the university website.\n"
    enroll_text += "4️⃣ Wait for admission results and apply for a visa.\n"
    enroll_text += "Need help? Ask me!"
    await update.message.reply_text(enroll_text)

async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:  # No category selected
        categories = get_faq_categories()
        # Display one category per row
        keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in categories]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please choose a category:", reply_markup=reply_markup)
    else:  # Category selected
        category = " ".join(context.args)
        context.user_data["selected_category"] = category  # Store the selected category
        questions = get_faq_questions_by_category(category)
        if questions:
            # Number the questions for reference
            numbered_questions = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
            keyboard = [
                [InlineKeyboardButton("Back to Categories", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Here are the questions in the '{category}' category:\n{numbered_questions}\n\nSend me the question number to get the answer.",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("No questions found in this category.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "back":  # Handle the "Back to Categories" button
        categories = get_faq_categories()
        keyboard = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in categories]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Please choose a category:", reply_markup=reply_markup)
    elif query.data.startswith("back_to_questions_"):  # Handle the "Back to Questions" button
        category = query.data.split("_")[-1]  # Extract the category from the callback data
        context.user_data["selected_category"] = category  # Store the selected category
        questions = get_faq_questions_by_category(category)
        if questions:
            numbered_questions = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
            keyboard = [
                [InlineKeyboardButton("Back to Categories", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                f"Here are the questions in the '{category}' category:\n{numbered_questions}\n\nSend me the question number to get the answer.",
                reply_markup=reply_markup
            )
        else:
            await query.message.reply_text("No questions found in this category.")
    else:  # Handle category selection
        category = query.data
        context.user_data["selected_category"] = category  # Store the selected category
        questions = get_faq_questions_by_category(category)
        if questions:
            numbered_questions = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
            keyboard = [
                [InlineKeyboardButton("Back to Categories", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                f"Here are the questions in the '{category}' category:\n{numbered_questions}\n\nSend me the question number to get the answer.",
                reply_markup=reply_markup
            )
        else:
            await query.message.reply_text("No questions found in this category.")

async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    try:
        question_number = int(user_input) - 1  # Convert to zero-based index
        if "selected_category" in context.user_data:  # Check if a category is selected
            category = context.user_data["selected_category"]
            questions = get_faq_questions_by_category(category)
            if questions:
                if 0 <= question_number < len(questions):  # Validate the question number
                    question = questions[question_number]
                    answer = get_faq_answer(question)
                    # Replace escaped newlines with actual newlines
                    formatted_answer = answer.replace('\\n', '\n')
                    # Add a "Back to Questions" button
                    keyboard = [[InlineKeyboardButton("Back to Questions", callback_data=f"back_to_questions_{category}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    # Send the formatted answer with the button
                    await update.message.reply_text(formatted_answer, reply_markup=reply_markup)
                else:
                    await update.message.reply_text("Invalid question number. Please try again.")
            else:
                await update.message.reply_text("No questions found in this category.")
        else:
            await update.message.reply_text("Please select a category first using /FAQ.")
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")


# Main function to run the bot
def main(): 
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('enroll', enroll_command)) 
    app.add_handler(CommandHandler('FAQ', faq_command))  
    app.add_handler(CallbackQueryHandler(button_callback))  
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer_question))  # Handle question numbers

    print('Bot is running!')
    app.run_polling()

if __name__ == '__main__':
    main()

















