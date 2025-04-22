#!/usr/bin/env python3
"""
Startup script for the scheduler service.
Run this separately from the main application to handle the scheduled tasks.
"""
import asyncio
import logging
from scheduler.scheduler import run_scheduler
from utils.logger import setup_logger
# Setup logger
logger = setup_logger("scheduler_startup")
if __name__ == "__main__":
    logger.info("Starting scheduler service")
    try:
        run_scheduler()
    except KeyboardInterrupt:
        logger.info("Scheduler service stopped by user")
    except Exception as e:
        logger.error(f"Scheduler service error: {e}")
