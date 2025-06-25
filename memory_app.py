#!/usr/bin/env python3
"""
Unified Memory Application

This application provides a complete memory management system that can:
1. Load configuration from config.json
2. Process markdown files from configured directories
3. Extract facts and create memories
4. Provide interactive chat functionality

Usage:
    python memory_app.py --help
    python memory_app.py process --config config.json
    python memory_app.py chat --config config.json
    python memory_app.py reset --config config.json
"""

import argparse
import logging
import sys
from pathlib import Path
from memory_manager import MemoryManager
from markdown_processor import MarkdownProcessor


def setup_logging(config_path: str = "config.json"):
    """
    Setup logging based on configuration.
    
    Args
    ----
    config_path: Path to configuration file
    """
    try:
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        log_config = config.get('logging', {})
        level = getattr(logging, log_config.get('level', 'INFO'))
        log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = log_config.get('file', 'memory_app.log')
        
        # Setup logging with both file and console handlers
        logging.basicConfig(
            level=level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
    except Exception as e:
        # Fallback logging setup
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        logging.warning(f"Could not load logging config: {e}")


def process_command(args):
    """
    Process markdown files and create memories.
    
    Args
    ----
    args: Parsed command line arguments
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize memory manager
        logger.info("Initializing Memory Manager...")
        memory_manager = MemoryManager(args.config)
        
        # Initialize markdown processor
        logger.info("Initializing Markdown Processor...")
        processor = MarkdownProcessor(memory_manager)
        
        # Process directories
        logger.info("Starting markdown processing...")
        files_processed, total_facts, added_facts = processor.process_directories(args.user)
        
        # Summary
        print("\n" + "=" * 60)
        print("PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Files processed: {files_processed}")
        print(f"Total facts extracted: {total_facts}")
        print(f"Successfully added facts: {added_facts}")
        print(f"Success rate: {(added_facts/total_facts*100):.1f}%" if total_facts > 0 else "No facts extracted")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


def chat_command(args):
    """
    Start interactive chat with memories.
    
    Args
    ----
    args: Parsed command line arguments
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize memory manager
        logger.info("Initializing Memory Manager...")
        memory_manager = MemoryManager(args.config)
        
        # Check if there are any memories
        all_memories = memory_manager.get_all_memories(args.user)
        if not all_memories or not all_memories.get('results'):
            print(f"⚠️  No memories found for user '{args.user}'")
            print("You may need to run 'process' command first to create memories from markdown files.")
            return
        
        memory_count = len(all_memories['results'])
        print(f"💭 Found {memory_count} memories for {args.user}")
        print("🤖 Memory Chat - Ask questions about your stored information")
        print("=" * 60)
        print("Type 'exit', 'quit', or 'q' to quit")
        print("Type 'memories' to see all stored memories")
        print("Type 'reset' to clear all memories")
        print()
        
        while True:
            try:
                user_input = input(f"{args.user}> ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("Goodbye! 👋")
                    break
                
                elif user_input.lower() == 'memories':
                    memories = memory_manager.get_all_memories(args.user)
                    if memories and memories.get('results'):
                        print(f"\n📚 All memories for {args.user}:")
                        for i, memory in enumerate(memories['results'], 1):
                            created_at = memory.get('created_at', 'Unknown time')
                            print(f"{i:2d}. {memory['memory']} (Created: {created_at})")
                    else:
                        print("No memories found.")
                    print()
                    continue
                
                elif user_input.lower() == 'reset':
                    confirm = input("Are you sure you want to delete all memories? (yes/no): ").strip().lower()
                    if confirm == 'yes':
                        deleted = memory_manager.reset_memories(args.user)
                        print(f"✅ Deleted {deleted} memories")
                    else:
                        print("Reset cancelled")
                    print()
                    continue
                
                elif not user_input:
                    continue
                
                # Get chat response
                print("🤔 Thinking...")
                response = memory_manager.chat(user_input, args.user)
                print(f"🤖 {response}")
                print()
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except EOFError:
                print("\nGoodbye! 👋")
                break
                
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        sys.exit(1)


def reset_command(args):
    """
    Reset all memories for a user.
    
    Args
    ----
    args: Parsed command line arguments
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize memory manager
        logger.info("Initializing Memory Manager...")
        memory_manager = MemoryManager(args.config)
        
        # Confirm reset
        if not args.force:
            confirm = input(f"Are you sure you want to delete all memories for '{args.user}'? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print("Reset cancelled")
                return
        
        # Reset memories
        deleted = memory_manager.reset_memories(args.user)
        print(f"✅ Deleted {deleted} memories for user '{args.user}'")
        
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        sys.exit(1)


def main():
    """
    Main application entry point.
    """
    parser = argparse.ArgumentParser(
        description="Unified Memory Application - Process markdown files and chat with memories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s process --config config.json --user bruce
  %(prog)s chat --config config.json --user bruce
  %(prog)s reset --config config.json --user bruce --force
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process markdown files and create memories')
    process_parser.add_argument('--config', '-c', default='config.json',
                               help='Path to configuration file (default: config.json)')
    process_parser.add_argument('--user', '-u', help='User ID for the memories (overrides config)')

    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Interactive chat with memories')
    chat_parser.add_argument('--config', '-c', default='config.json',
                            help='Path to configuration file (default: config.json)')
    chat_parser.add_argument('--user', '-u', help='User ID for the memories (overrides config)')

    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset all memories for a user')
    reset_parser.add_argument('--config', '-c', default='config.json',
                             help='Path to configuration file (default: config.json)')
    reset_parser.add_argument('--user', '-u', help='User ID for the memories (overrides config)')
    reset_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Setup logging
    setup_logging(args.config)
    
    # Validate config file exists
    if not Path(args.config).exists():
        print(f"❌ Configuration file not found: {args.config}")
        sys.exit(1)
    
    # Set default user if not provided
    if not hasattr(args, 'user') or not args.user:
        try:
            import json
            with open(args.config, 'r') as f:
                config = json.load(f)
            args.user = config.get('processing_options', {}).get('user_id', 'default')
        except Exception:
            args.user = 'default'
    
    # Execute command
    if args.command == 'process':
        process_command(args)
    elif args.command == 'chat':
        chat_command(args)
    elif args.command == 'reset':
        reset_command(args)


if __name__ == "__main__":
    main()
