import asyncio
from dotenv import load_dotenv
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from kb import create_vector_store
from deep_agents import create_agent
from loguru import logger
from telegram.constants import ParseMode
import telegramify_markdown
from telegramify_markdown.customize import get_runtime_config
from langgraph.store.postgres.aio import AsyncPostgresStore
import constants as c

cfg = get_runtime_config()
cfg.markdown_symbol.heading_level_1 = "📌"
cfg.markdown_symbol.link = "🔗"
cfg.cite_expandable = True


load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AGENT = None


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    result = await AGENT.ainvoke(
        {"messages": [{"role": "user", "content": update.message.text}]},
        config={"configurable": {"thread_id": str(update.effective_chat.id), "assistant_id": str(update.effective_user.id), "user_name": update.effective_user.first_name}},
    )
    logger.info(result)
    response_text = str(result["structured_response"]["response"])
    converted = telegramify_markdown.markdownify(
        response_text,
        max_line_length=None,  # If you want to change the max line length for links, images, set it to the desired value.
        normalize_whitespace=False,
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=converted, parse_mode=ParseMode.MARKDOWN_V2)


async def start(update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
    )


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hello {update.effective_user.first_name}")


async def main():
    # logger.info("Creating vector store")
    # store = await create_vector_store()
    global AGENT
    async with AsyncPostgresStore.from_conn_string(c.CONNECTION_STRING) as store:
        await store.setup()

        AGENT = create_agent(store)
        logger.info("Agent started")

        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

        # Handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("hello", hello))
        application.add_handler(
            MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
        )

        try:
            # ---- START ----
            await application.initialize()
            await application.start()
            await application.updater.start_polling()

            logger.info("Telegram bot started")

            # Keep running forever
            await asyncio.Event().wait()

        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Shutdown signal received")

        finally:
            # ---- CLEANUP (VERY IMPORTANT) ----
            logger.info("Stopping Telegram bot...")

            await application.updater.stop()
            await application.stop()
            await application.shutdown()

            logger.info("Telegram bot stopped cleanly")

if __name__ == "__main__":
    logger.add("logs/bot_{time}.log", rotation="10 MB", retention="10 days")
    asyncio.run(main())
    
